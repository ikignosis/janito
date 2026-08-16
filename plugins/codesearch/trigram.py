"""
Trigram extraction and query construction.

This module implements the trigram extraction logic described in
Russ Cox's "Regular Expression Matching with a Trigram Index"
(https://swtch.com/~rsc/regexp/regexp4.html).

A trigram is a sequence of 3 consecutive characters.  The inverted index
maps each trigram to the set of documents (files) that contain it.
For keyword search we extract all trigrams from each keyword and
construct an AND/OR query over the posting lists.
"""


def extract_trigrams(text: str) -> set[str]:
    """
    Extract all trigrams from a text string.

    Args:
        text: The input text.

    Returns:
        A set of trigram strings (3-character substrings).
        If the text has fewer than 3 characters, returns an empty set
        (meaning ANY document could match -- the caller must handle this).
    """
    if len(text) < 3:
        return set()
    return {text[i : i + 3] for i in range(len(text) - 2)}


def trigrams_for_keyword(keyword: str) -> set[str]:
    """
    Return the set of trigrams that must ALL be present in a document
    for the keyword to appear.

    For keywords of 3+ characters this is the set of overlapping
    3-character substrings.  For shorter keywords we return an empty
    set, which the caller should interpret as "match all documents"
    (the same convention as Russ Cox's ANY query).

    Args:
        keyword: The search keyword.

    Returns:
        A set of trigrams.  Empty set means the keyword is too short
        to use trigram indexing (fewer than 3 characters).
    """
    if len(keyword) < 3:
        return set()
    return extract_trigrams(keyword)


def build_trigram_query(keywords: list[str]) -> dict[str, set[str]]:
    """
    Build a trigram query from a list of keywords.

    For each keyword we compute the set of trigrams that must all be
    present.  The overall query is the union of these per-keyword sets
    when using AND semantics, or the per-keyword sets when using OR.

    Args:
        keywords: List of search keywords.

    Returns:
        A dict mapping each keyword to its trigram set.
        Keywords shorter than 3 characters map to an empty set.
    """
    result: dict[str, set[str]] = {}
    for kw in keywords:
        result[kw] = trigrams_for_keyword(kw)
    return result
