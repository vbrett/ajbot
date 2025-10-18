''' manage AJ database
'''
from datetime import datetime, date, time
from thefuzz import fuzz
import humanize
from discord.ext.commands import MemberConverter, MemberNotFound
from vbrpytools.exceltojson import ExcelWorkbook

from ajbot._internal.exceptions import OtherException, AjDbException
from ajbot._internal.config import AJ_TABLE_NAME_EVENTS, AJ_TABLE_NAME_ROSTER

class AjDate(date):
    """ class that handles date type for AJ DB
    """
    def __new__(cls, indate, *args, **kwargs):
        #check if first passed argument is already a datetime format
        if isinstance(indate, (datetime, date)):
            return super().__new__(cls, indate.year, indate.month, indate.day, *args, **kwargs)
        if isinstance(indate, time):
            return None
        return super().__new__(cls, indate, *args, **kwargs)

    def __format__(self, _):
        humanize.i18n.activate("fr_FR")
        return humanize.naturaldate(self)


class AjMemberId(int):
    """ Class that handles AJ member id as integer, and represents it in with correct format
    """
    def __str__(self):
        return f"AJ-{str(int(self)).zfill(5)}"

AJ_MEMBER_ATTR = {"id": ("id", AjMemberId),
                  "creation_date" : ("creation.date", AjDate),
                  "last_name" : ("nom", str),
                  "first_name" : ("prenom", str),
                  "friendly_name" : ("nom_userfriendly", str),
                  "discord" : ("pseudo_discord", str),
                  "membership_total" : ("stats.cotis.nb", int),
                  "membership_last" : ("stats.cotis.derniere", AjDate),
                  "last_activity" : ("stats.der_activite", AjDate),
                  "presence_total" : ("stats.presence.nb", int),
                  "season_presence" : ("saison.presence", int),
                  "season_membership" : ("saison.cotis", bool),
                  "season_role" : ("saison.asso_role", str),
                  "season_photo_authorized" : ("saison.utilisation_image", bool),
                 }

class AjMember():
    """ Class defining one member of AJ
    """
    # pylint: disable=no-member # disable in this class scope
    def __init__(self, input_dict):
        #Map each input_dict key to an actual variable, converted to proper type
        for varname, varinfo in AJ_MEMBER_ATTR.items():
            val = input_dict.get(varinfo[0], None)
            if val and varinfo[1] and not isinstance(val, varinfo[1]):
                val = varinfo[1](val)
            setattr(self, varname, val)

    def __format__(self, format_spec="short"):
        """ override format
        """
        match format_spec:
            case "short":
                member_info = [f"{self.id}",
                               " ".join([self.first_name, self.last_name]) if self.first_name or self.last_name else None,
                               f"@{self.discord}" if self.discord else None,
                              ]
                return " - ".join([x for x in member_info if x])

            case _:
                return "this format is not supported (yet)"


class AjMatchedMember():
    """ Class to handled AJ member with a match value
    """
    def __init__(self, member, match_val):
        self.member = member
        self.match_val = match_val

    def __format__(self, format_spec="short"):
        """ override format
        """
        return f"{self.member:{format_spec}} (matche à {self.match_val}%)"
        # return self.member.__format__(format_spec) + f" (matche à {self.match_val}%)"


class AjMembers(dict):
    """ Class handling AJ member roster
    """
    def __init__(self, input_list):
        super().__init__()
        self.update({AjMemberId(m["id"]) : AjMember(m) for m in input_list})

    async def search(self, lookup_val,
                     discord_ctx = None, match_crit = 50,
                     break_if_multi_perfect_match = True,):
        ''' retrieve list of member ids matching lookup_val which can be
                - integer = member ID
                - discord pseudo (needs discord_ctx)
                - string that is compared to "user friendly name" using fuzzy search

            for first 2 types, return exact match
            for last, return exact match if found, otherwise list of match above match_crit
            In case of multiple perfect match, raise exception if asked

            @return
                [member (if perfect match) or matchedMember (if not perfect match)]
        '''
        # Try to convert to discord member. If succeed, search using discord name
        if discord_ctx:
            try:
                lookup_val = await MemberConverter().convert(discord_ctx, lookup_val)
                return [v for v in self.values()
                        if v.discord == lookup_val.name]
            except MemberNotFound:
                pass

        # Try to convert to integer. If succeed, search using member id
        try:
            lookup_val = int(lookup_val)
            return [v for k, v in self.items()
                    if k == lookup_val]
        except ValueError:
            pass

        # Fuzz search on friendly name
        fuzzy_match = [AjMatchedMember(v, fuzz.token_sort_ratio(lookup_val, v.friendly_name))
                       for v in self.values()]
        fuzzy_match = [v for v in fuzzy_match if v.match_val > match_crit]
        fuzzy_match.sort(key=lambda x: x.match_val, reverse=True)

        perfect_match = [v.member for v in fuzzy_match if v.match_val == 100]
        if perfect_match:
            if len(perfect_match) > 1 and break_if_multi_perfect_match:
                raise AjDbException(f"multiple member perfectly match {lookup_val}")
            return perfect_match

        return fuzzy_match






AJ_EVENT_ATTR = {"id": ("#support.id", int),
                 "date" : ("date", AjDate),
                 "in_season": ("#support.saison_en_cours", bool),
                 "type": ("entree.categorie", str),
                 "name": ("entree.nom", str),
                 "detail": ("entree.detail", str),
                 "member_id": ("membre.id", AjMemberId),
                #  "": ("membre.asso_role", str),
                #  "": ("compta.compte", None),
                #  "": ("compta.credit", None),
                #  "": ("compta.debit", None),
                #  "": ("commentaire", None),
                 "member_friendly_name": ("#support.nom", str),
                #  "": ("#support.nb_in_suivi", None),
                #  "": ("membre.prive.nom", None),
                #  "": ("membre.prive.prenom", None),
                #  "": ("membre.prive.date_naissance", None),
                #  "": ("membre.prive.[emails]", None),
                #  "": ("membre.prive.[telephone]", None),
                #  "": ("membre.prive.adresse.numero", None),
                #  "": ("membre.prive.adresse.type_voie", None),
                #  "": ("membre.prive.adresse.nom_voie", None),
                #  "": ("membre.prive.adresse.autre", None),
                #  "": ("membre.prive.adresse.cpmembre.prive.adresse.ville", None),
                #  "": ("membre.prive.pseudo_discord", str),
                #  "": ("membre.prive.approbation_statuts", None),
                #  "": ("membre.prive.assurance_resp_civile", None),
                #  "": ("membre.prive.utilisation_image", None),
                #  "": ("membre.source_connaissance", None),
                #  "": ("#support.saison#support.evement", None),
                #  "": ("#support.traite_manuel", None),
                #  "": ("#support.traite", None),
                }

class AjEvent():
    """ Class defining one event of AJ
    """
    # pylint: disable=no-member # disable in this class scope
    def __init__(self, input_dict):
        #Map each input_dict key to an actual variable, converted to proper type
        for varname, varinfo in AJ_EVENT_ATTR.items():
            val = input_dict.get(varinfo[0], None)
            if val and varinfo[1] and not isinstance(val, varinfo[1]):
                val = varinfo[1](val)
            setattr(self, varname, val)

    EVENT_TYPE_PRESENCE = "Présence"
    EVENT_TYPE_EVENT = "Evènement"
    EVENT_TYPE_CONTRIBUTION = "Cotisation"
    EVENT_TYPE_MEMBER_INFO = "Info Membre"
    EVENT_TYPE_MGMT = "Gestion"
    EVENT_TYPE_PURCHASE = "Achat"

    def __format__(self, format_spec=""):
        """ override format
        """
        # match format_spec:
        #     case "short":
        #         member_info = [f"{self.id}",
        #                        " ".join([self.first_name, self.last_name]) if self.first_name or self.last_name else None,
        #                        f"@{self.discord}" if self.discord else None,
        #                       ]
        #         return " - ".join([x for x in member_info if x])

        #     case _:
        return "this format is not supported (yet)"


class AjEvents(list):
    """ Class handling AJ events
    """
    def __init__(self, input_list):
        super().__init__()
        self.extend(AjEvent(e) for e in input_list)

    def get_in_season_events(self, event_types = None):
        """ returns events of certain type that are in current season
        """
        if event_types and not isinstance(event_types, list):
            event_types = [event_types]

        return [event for event in self if event.in_season and (not event_types or event.type in [etype for etype in event_types])]



class AjDb():
    ''' manage AJ database
    '''
    def __init__(self, xls_file):
        self._wb = ExcelWorkbook(xls_file)
        self.members = AjMembers(self._wb.dict_from_table(AJ_TABLE_NAME_ROSTER, nested=False, with_ignored=True))
        self.events = AjEvents(self._wb.dict_from_table(AJ_TABLE_NAME_EVENTS, nested=False, with_ignored=True))


if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
