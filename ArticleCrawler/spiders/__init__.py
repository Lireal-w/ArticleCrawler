# This package will contain the spiders of your Scrapy project
#
# Please refer to the documentation for information on how to create and manage
# your spiders.

from .affpapa import AffpapaSpider
from .bnldata import BnldataSpider
from .envMedia import EnvmediaSpider
from .focusgn import FocusgnSpider
from .gamblinginsider import GamblinginsiderSpider
from .igamingbusiness import IgamingbusinessSpider
from .intergameonline import IntergameonlineSpider
from .sbcnews import SbcnewsSpider
from .sigma import SigmaSpider
from .lance import LanceSpider

spiders = [
    AffpapaSpider,
    BnldataSpider,
    EnvmediaSpider,
    FocusgnSpider,
    GamblinginsiderSpider,
    IgamingbusinessSpider,
    IntergameonlineSpider,
    SbcnewsSpider,
    SigmaSpider,
    # LanceSpider
]
