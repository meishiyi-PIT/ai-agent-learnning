from dataclasses import dataclass
from typing import Literal

RenewalDecision = Literal[
    "RENEW_ORIGINAL",
    "UPGRADE",
    "NEED_MORE_INFORMATION",
    "CANNOT_DETERMINE",
]

@dataclass(frozen=True)
class RenewalOption:
    option_code:str
    option_name:str
    permium_cents:int

RENEWAL_OPTIONS = (
    RenewalOption(
        option_code="RENEW_ORIGINAL",
        option_name="原方案续保",
        permium_cents=39_900,
    ),
    RenewalOption(
        option_code="UPGRADE",
        option_name="升级保障方案",
        permium_cents=59_900
    ),
)

def find_renewal_option(option_code:str)->RenewalOption|None:
    """按代号查找候选方案，供提交工具校验使用，找不到返回none"""
    for option in RENEWAL_OPTIONS:
        if option.option_code == option_code:
            return option

    return None    