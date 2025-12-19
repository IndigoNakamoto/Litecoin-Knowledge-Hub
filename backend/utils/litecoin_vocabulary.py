import re
from typing import Dict

# 1. Expanded and categorized synonym map
LTC_SYNONYM_MAP: Dict[str, str] = {
    # --- Privacy & MWEB ---
    "mimblewimble": "mweb",
    "extension blocks": "mweb",
    "privacy upgrade": "mweb",
    "confidential transactions": "mweb",
    "mw": "mweb",
    "eb": "mweb",
    
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
    "litvm": "litvm",
    "litecoin virtual machine": "litvm",
    "zero-knowledge omnichain": "litvm",
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
    "trezor": "custody",

    # --- Other ---
    "blocktime": "litecoin block time",
    "block time": "litecoin block time",
    "hashrate": "litecoin hashrate",
    "supply": "litecoin supply",
    "address": "litecoin address",
    "transaction": "litecoin transaction",
    "transactions": "litecoin transactions",
    "block": "litecoin block",
    "blocks": "litecoin blocks",
    "network": "litecoin network",
    "networks": "litecoin networks",
    "node": "litecoin node",
    "nodes": "litecoin nodes",
    "peer": "litecoin peer",
    "peers": "litecoin peers",
    "peer-to-peer": "litecoin peer-to-peer",
    "p2p": "litecoin peer-to-peer",
    "p2p network": "litecoin peer-to-peer network",
    "p2wpkh": "bech32",
    "p2wsh": "bech32",
    "lip-2": "mweb",
}

# Entity expansion map for rare terms that need synonym boosting in retrieval
# Unlike LTC_SYNONYM_MAP (which replaces terms), this APPENDS synonyms to improve
# semantic search recall for queries containing these entities.
LTC_ENTITY_EXPANSIONS: Dict[str, str] = {
    # --- Existing (Kept for context) ---
    "litvm": "litecoin virtual machine zero-knowledge omnichain smart contracts",
    "mweb": "mimblewimble extension blocks privacy confidential transactions lip-0002 lip-0003", # Added LIPs
    "scrypt": "hashing algorithm mining proof of work",
    "halving": "block reward reduction subsidy economics issuance",
    "lightning": "lightning network payment channels layer 2 scaling off-chain",
    "ordinals": "inscriptions tokens ltc-20 nft digital artifacts",
    "auxpow": "merged mining doge mining auxiliary proof of work",

    # --- NEW: Protocol & Upgrades ---
    "segwit": "segregated witness transaction malleability block weight capacity upgrade bip141",
    "taproot": "schnorr signatures mast privacy smart contracts upgrade bip341",
    "atomic swaps": "cross-chain decentralized exchange htlc interoperability swap",
    "csv": "checksequenceverify timelock relative locktime smart contract",
    "cltv": "checklocktimeverify timelock absolute locktime smart contract",
    
    # --- NEW: Addressing & Standards ---
    "bech32": "native segwit address format ltc1 prefix efficiency",
    "p2sh": "pay to script hash multisig compatibility m-address 3-address",
    "ltc-20": "brc-20 standard fungible tokens json experimental overlay protocol",
    "omnilite": "omni layer tokens stablecoin usdt assets",

    # --- NEW: Network & Infrastructure ---
    "mempool": "memory pool unconfirmed transactions fee estimation congestion",
    "difficulty": "mining difficulty retarget adjustment hashrate security",
    "litecoin core": "reference client full node daemon wallet software",
    "electrum-ltc": "spv wallet lightweight client deterministic seed",
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


def expand_ltc_entities(query: str) -> str:
    """
    Expands known entities with synonyms to improve retrieval recall.
    
    Unlike normalize_ltc_keywords() which replaces terms, this function
    APPENDS synonyms to the query when rare entities are detected. This
    helps semantic search find relevant documents that use different
    terminology for the same concept.
    
    Example:
        "explain litvm" -> "explain litvm litecoin virtual machine zero-knowledge omnichain smart contracts"
    
    Args:
        query: User input string (typically after normalization).
    Returns:
        Query with appended synonyms for detected entities.
    """
    if not query:
        return ""
    
    query_lower = query.lower()
    expansions_to_add = []
    
    for entity, expansion in LTC_ENTITY_EXPANSIONS.items():
        # Check if entity is in query but expansion terms are not already present
        if entity in query_lower:
            # Only add expansion if it's not already in the query
            expansion_terms = expansion.split()
            new_terms = [term for term in expansion_terms if term not in query_lower]
            if new_terms:
                expansions_to_add.extend(new_terms)
    
    if expansions_to_add:
        # Append unique expansion terms to the query
        return f"{query} {' '.join(expansions_to_add)}".strip()
    
    return query.strip()