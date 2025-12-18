import re
from typing import Dict

# 1. Expanded and categorized synonym map
LTC_SYNONYM_MAP: Dict[str, str] = {
    # --- Privacy & MWEB ---
    "mimblewimble": "mweb",
    "extension blocks": "mweb",
    "privacy upgrade": "mweb",
    "confidential transactions": "mweb",
    "stealth addresses": "mweb",
    "mw": "mweb",
    "eb": "mweb",
    "hogex": "mweb", # MWEB-specific transaction type
    
    # --- Economics, Supply & Halving ---
    "total coins": "supply",
    "circulating supply": "supply",
    "issuance": "supply",
    "inflation": "supply",
    "max supply": "supply",
    "halvening": "halving",
    "block reward reduction": "halving",
    "subsidy": "halving",
    "stock to flow": "economics",
    "scarcity": "economics",
    
    # --- Leadership, Governance & History ---
    "charlie lee": "creator",
    "coblee": "creator",
    "founder": "creator",
    "litecoin foundation": "foundation",
    "lf": "foundation",
    "genesis block": "history",
    "fair launch": "history",
    "silver to gold": "narrative",
    "digital silver": "narrative",
    
    # --- Mining & Security ---
    "mining algorithm": "scrypt",
    "hashing algorithm": "scrypt",
    "pow": "proof of work",
    "hashrate": "security",
    "51% attack": "security",
    "double spend": "security",
    "asic": "mining hardware",
    "l7": "mining hardware", # Antminer L7 is dominant for LTC
    "merged mining": "auxpow",
    "doge mining": "auxpow",
    
    # --- Layer 2, Scaling & Assets ---
    "lightning network": "lightning",
    "l2": "lightning",
    "payment channels": "lightning",
    "omnilite": "smart contracts",
    "tokens": "ordinals",
    "inscriptions": "ordinals",
    "brc-20": "ltc-20", # Mapping the BTC equivalent to the LTC version
    "taproot": "upgrades",
    "segwit": "upgrades",
    "bech32": "address format",
    
    # --- Wallet & Integration ---
    "litewallet": "wallet",
    "loafwallet": "wallet", # Former name of Litewallet
    "electrum-ltc": "wallet",
    "cold storage": "custody",
    "hardware wallet": "custody",
    "ledger": "custody",
    "trezor": "custody"
}

# 2. Pre-compile the regex for O(1) invocation performance
# We sort by length descending to ensure longest matches are prioritized
_SORTED_SYNONYMS = sorted(LTC_SYNONYM_MAP.keys(), key=len, reverse=True)
_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(s) for s in _SORTED_SYNONYMS) + r')\b', 
    flags=re.IGNORECASE
)

def normalize_ltc_keywords(query: str) -> str:
    """
    Normalizes query using a single-pass regex for high-performance mapping.
    
    Args:
        query: User input string.
    Returns:
        Normalized string with canonical terms.
    """
    if not query:
        return ""

    # The lambda function looks up the lowercase match in our map
    return _PATTERN.sub(
        lambda m: LTC_SYNONYM_MAP[m.group(0).lower()], 
        query
    ).strip()