__all__ = ['get_agent_texts_for_pmids',
           'get_stmts_with_agent_text_like',
           'get_text_content_from_stmt_ids',
           'get_agent_stmt_counts',
           'get_stmts_with_agent_text_in',
           'get_text_content_from_pmids',
           'get_text_content_from_stmt_ids',
           'get_text_content_from_text_refs']

from sqlalchemy import text
from contextlib import closing
from functools import lru_cache
from collections import defaultdict, Counter

from .constructors import get_primary_db
from .helpers import unpack, _get_trids


def get_agent_texts_for_pmids(pmids, open_db=None):
    """Return list of raw agent text extracted from a list of pmids

    Parameters
    ----------
    pmids : list
        pmids as list of strings

    open_db : Optional[callable]
        Function that constructs a DatabaseManager. If None, uses
        get_primary_db. Default: None

    Returns
    -------
    dict
        Dictionary giving counts of raw agent texts extracted from texts
        with the given pmids.
    """
    if open_db is None:
        open_db = get_primary_db
    with closing(open_db()) as db:
        pmids = tuple(pmids)
        query = """
                SELECT
                    tr.pmid, ARRAY_AGG(ra.db_id)
                FROM
                    text_ref tr
                JOIN
                    raw_stmt_ref_link link
                ON
                    link.text_ref_id = tr.id
                JOIN
                    raw_agents ra
                ON
                    ra.stmt_id = link.stmt_id
                WHERE
                    ra.db_name LIKE 'TEXT'
                AND
                    ra.db_id IS NOT NULL
                AND
                    tr.pmid IN :pmids
                GROUP BY
                    pmid
                """
        res = db.session.execute(text(query), {'pmids': pmids})
    return {pmid: dict(Counter(agent_texts)) for pmid, agent_texts in res}


def get_stmts_with_agent_text_like(pattern, filter_genes=False,
                                   open_db=None):
    """Get statement ids with agent with rawtext matching pattern


    Parameters
    ----------
    pattern : str
        a pattern understood by sqlalchemy's like operator.
        For example '__' for two letter agents

    filter_genes : Optional[bool]
       if True, only returns map for agent texts for which there is at least
       one HGNC grounding in the database. Default: False

    open_db : Optional[callable]
        Function that constructs a DatabaseManager. If None, uses
        get_primary_db. Default: None

    Returns
    -------
    dict
        dict mapping agent texts to statement ids. agent text are those
        matching the input pattern. Each agent text maps to the list of
        statement ids for statements containing an agent with that TEXT
        in its db_refs
    """
    if open_db is None:
        open_db = get_primary_db
    with closing(open_db()) as db:
        # Query Raw agents table for agents with TEXT db_ref matching pattern
        # Selects agent texts, statement ids and agent numbers. The agent number
        # corresponds to the agents index into the agent list
        agents = db.select_all([db.RawAgents.db_id,
                                db.RawAgents.stmt_id,
                                db.RawAgents.ag_num],
                               db.RawAgents.db_name.like('TEXT'),
                               db.RawAgents.db_id.like(pattern),
                               db.RawAgents.stmt_id.isnot(None))
        if filter_genes:
            # If filtering to only genes, get statement ids and agent numbers
            # for all agents grounded to HGNC. Check if agent text has been
            # grounded to HGNC at least once
            hgnc_agents = db.select_all([db.RawAgents.stmt_id,
                                         db.RawAgents.ag_num],
                                        db.RawAgents.db_name.like('HGNC'),
                                        db.RawAgents.stmt_id.isnot(None))
            hgnc_agents = set(hgnc_agents)
            agents = [(agent_text, stmt_id, ag_num)
                      for agent_text, stmt_id, ag_num in agents
                      if (stmt_id, ag_num) in hgnc_agents]
    output = defaultdict(list)
    for agent_text, stmt_id, ag_num in agents:
        if stmt_id not in output[agent_text]:
            output[agent_text].append(stmt_id)
    return dict(output)


def get_agent_stmt_counts(agent_texts, open_db=None):
    if open_db is None:
        open_db = get_primary_db
    with closing(open_db()) as db:
        agent_texts = tuple(set(agent_texts))
        query = """
                SELECT
                    db_id, Count(stmt_id)
                FROM
                    raw_agents
                WHERE
                    db_name LIKE 'TEXT'
                AND
                    db_id IN :agent_texts
                AND
                    stmt_id IS NOT NULL
                GROUP BY
                    db_id
                """
        res = db.session.execute(text(query), {'agent_texts': agent_texts})
    return {agent_text: count for agent_text, count in res}


def get_stmts_with_agent_text_in(agent_texts, filter_genes=False,
                                 open_db=None):
    """Get statement ids with agent with rawtext in list

    Parameters
    ----------
    agent_texts : list of str
        a list of agent texts

    filter_genes : Optional[bool]
        if True, only returns map for agent texts for which there is at least
        one HGNC grounding in the database. Default: False

    open_db : Optional[callable]
        Function that constructs a DatabaseManager. If None, uses
        get_primary_db. Default: None

    Returns
    -------
    dict
        dict mapping agent texts to lists of statement ids for statements
        containing an agent with that TEXT in its db_refs.
    """
    if open_db is None:
        open_db = get_primary_db

    with closing(open_db()) as db:
        # Query Raw agents table for agents with TEXT db_ref matching pattern
        # Selects agent texts, statement ids and agent numbers. The agent number
        # corresponds to the agents index into the agent list
        agents = db.select_all([db.RawAgents.db_id,
                                db.RawAgents.stmt_id,
                                db.RawAgents.ag_num],
                               db.RawAgents.db_name.like('TEXT'),
                               db.RawAgents.stmt_id.isnot(None))
        agents = [(agent_text, stmt_id, ag_num)
                  for agent_text, stmt_id, ag_num in agents
                  if agent_text in agent_texts]
        if filter_genes:
            # If filtering to only genes, get statement ids and agent numbers
            # for all agents grounded to HGNC. Check if agent text has been
            # grounded to HGNC at least once
            hgnc_agents = db.select_all([db.RawAgents.stmt_id,
                                         db.RawAgents.ag_num],
                                        db.RawAgents.db_name.like('HGNC'),
                                        db.RawAgents.stmt_id.isnot(None))
            hgnc_agents = set(hgnc_agents)
            agents = [(agent_text, stmt_id, ag_num)
                      for agent_text, stmt_id, ag_num in agents
                      if (stmt_id, ag_num) in hgnc_agents]
    output = defaultdict(list)
    for agent_text, stmt_id, ag_num in agents:
        if stmt_id not in output[agent_text]:
            output[agent_text].append(stmt_id)
    return dict(output)


def get_text_content_from_stmt_ids(stmt_ids):
    """Get text content for statements from a list of ids

    Gets the fulltext if it is available, even if the statement came from an
    abstract.

    Parameters
    ----------
    stmt_ids : list of ints

    Returns
    -------
    ref_dict: dict
        dict mapping statement ids to identifiers for pieces of content.
        These identifiers take the form `<text_ref_id>/<source>/<text_type>'.
        No entries exist for statements with no associated text content
        (these typically come from databases)


    text_dict: dict
        dict mapping content identifiers used as values in the ref_dict
        to best available text content. The order of preference is
        fulltext xml > plaintext abstract > title
    """
    identifiers = get_content_identifiers_from_stmt_ids(stmt_ids)
    content = _get_text_content(identifiers.values())
    return identifiers, content


def get_text_content_from_pmids(pmids, db=None):
    """Get best available text content for list of pmids

    For each pmid, gets the best piece of text content with the priority
    fulltext > abstract > title.

    Parameters
    ----------
    pmids : list of str

    Returns
    -------
    identifiers : dict
        dict mapping pmids to identifiers for pieces of content.
        These identifiers are tuples of the form
        (text_ref_id, source, text_type). Each tuple uniquely specifies
        a piece of content in the database
        No entries exist for statements with no associated text content
        (these typically come from databases)

    content : dict
        dict mapping content identifiers used as values in the ref_dict
        to the best available text content.
    """
    identifiers = get_content_identifiers_from_pmids(pmids)
    content = _get_text_content(identifiers.values())
    return identifiers, content


def get_content_identifiers_from_stmt_ids(stmt_ids, open_db=None):
    """Get content identifiers for statements from a list of ids

    An identifier is a triple containing a text_ref_id, source, and text_type
    Gets the identifier for best piece of text content with priority
    fulltext > abstract > title

    Parameters
    ----------
    stmt_ids : list of str

    open_db : Optional[callable]
        Function that constructs a DatabaseManager. If None, uses
        get_primary_db. Default: None

    Returns
    -------
    ref_dict: dict
        dict mapping statement ids to identifiers for pieces of content.
        These identifiers take the form `<text_ref_id>/<source>/<text_type>'.
        No entries exist for statements with no associated text content
        (these typically come from databases)
    """
    if open_db is None:
        open_db = get_primary_db
    stmt_ids = tuple(set(stmt_ids))
    with closing(open_db()) as db:
        query = """SELECT
                       sub.stmt_id, tc.text_ref_id, tc.source,
                       tc.format, tc.text_type
                   FROM
                       text_content tc,
                       (SELECT
                            stmt_id, text_ref_id
                        FROM
                            raw_stmt_ref_link
                        WHERE
                            stmt_id IN :stmt_ids) sub
                    WHERE
                        tc.text_ref_id = sub.text_ref_id
                """
        res = db.session.execute(text(query), {'stmt_ids': stmt_ids})
    return _collect_content_identifiers(res)


def get_content_identifiers_from_pmids(pmids, open_db=None):
    """Get content identifiers from list of pmids

    An identifier is a triple containing a text_ref_id, source, and text_type
    Gets the identifier for best piece of text content with priority
    fulltext > abstract > title

    Parameters
    ----------
    pmids : list of str

    open_db : Optional[callable]
        Function that constructs a DatabaseManager. If None, uses
        get_primary_db. Default: None

    Returns
    -------
    ref_dict: dict
        dict mapping statement ids to identifiers for pieces of content.
        These identifiers take the form `<text_ref_id>/<source>/<text_type>'.
        No entries exist for statements with no associated text content
        (these typically come from databases)


    text_dict: dict
        dict mapping content identifiers used as values in the ref_dict
        to best available text content. The order of preference is
        fulltext xml > plaintext abstract > title
    """
    if open_db is None:
        open_db = get_primary_db
    pmids = tuple(set(pmids))
    with closing(open_db()) as db:
        query = """SELECT
                       tr.pmid, tr.id, tc.source, tc.format, tc.text_type
                   FROM
                       text_content AS tc
                   JOIN
                       text_ref as tr
                   ON
                       tr.id = tc.text_ref_id
                   WHERE
                       tr.pmid IN :pmids
                """
        res = db.session.execute(text(query), {'pmids': pmids})
    return _collect_content_identifiers(res)


def _collect_content_identifiers(res):
    priority = {'fulltext': 2, 'abstract': 1, 'title': 0}
    seen_text_refs = {}
    ref_dict = {}
    for id_, text_ref_id, source, format_, text_type in res.fetchall():
        new_identifier = (text_ref_id, source, format_, text_type)
        if (id_, text_ref_id) not in seen_text_refs:
            seen_text_refs[(id_, text_ref_id)] = new_identifier
            ref_dict[id_] = new_identifier
        else:
            # update if we find text_type with higher priority for
            # a given text_ref
            old_identifier = seen_text_refs[(id_, text_ref_id)]
            old_text_type = old_identifier[3]
            if priority[text_type] > priority[old_text_type]:
                seen_text_refs[(id_, text_ref_id)] = new_identifier
                ref_dict[id_] = new_identifier
    return ref_dict


def _get_text_content(content_identifiers, open_db=None):
    """Return text_content associated to a list of content identifiers

    Parameters
    ----------
    content_identifiers : iterable of tuple
        A content identifier is a triple with three elements, text_ref_id,
        source, and text_type. These three pieces of information uniquely
        specify a piece of content in the database. content_identifiers
        is a list of these triples

    open_db : Optional[callable]
        Function that constructs a DatabaseManager. If None, uses
        get_primary_db. Default: None

    Returns
    -------
    dict
        A dictionary mapping content identifiers to pieces of
        text content. content identifiers for which no content
        exists in the database are excluded as keys.
    """
    if not content_identifiers:
        return {}
    if open_db is None:
        open_db = get_primary_db
    # Remove duplicate identifiers
    content_identifiers = set(content_identifiers)
    # Query finds content associated to each identifier by joining
    # the text_content table with a virtual table containing the
    # input identifiers. The query string is generated programmatically
    with closing(open_db()) as db:
        id_str = ', '.join('(:trid%d, :source%d, :format%d, :text_type%d)'
                           % (i, i, i, i)
                           for i in range(len(content_identifiers)))
        params = {}
        for i, (trid, source,
                format_, text_type) in enumerate(content_identifiers):
            params.update({'trid%s' % i: trid,
                           'source%i' % i: source,
                           'format%i' % i: format_,
                           'text_type%i' % i: text_type})
        query = """SELECT
                       tc.text_ref_id, tc.source, tc.format, tc.text_type,
                       content
                   FROM
                       text_content AS tc
                   JOIN (VALUES %s)
                   AS
                      ids (text_ref_id, source, format, text_type)
                   ON
                       tc.text_ref_id = ids.text_ref_id
                       AND tc.source = ids.source
                       AND tc.format = ids.format
                       AND tc.text_type = ids.text_type
                   WHERE
                       content IS NOT NULL
                """ % id_str
        res = db.session.execute(text(query), params)
    return {(trid, source, format, text_type): unpack(content)
            for trid, source, format, text_type, content in res}


def get_text_content_from_text_refs(text_refs, open_db=None, use_cache=True):
    """Get text_content from an evidence object's text_refs attribute


    Parameters
    ----------
    text_refs : dict of str: str
        text_refs dictionary as contained in an evidence object
        The dictionary should be keyed on id_types. The valid keys
        are 'PMID', 'PMCID', 'DOI', 'PII', 'URL', 'MANUSCRIPT_ID'.

    open_db : Optional[callable]
        Function that constructs a DatabaseManager. If None, uses
        get_primary_db. Default: None

    use_cache : Optional[bool]
        Whether or not to use cached results. Only relevant when
        querying the primary database. Will not work if primary
        database is passed in with keyword argument. Only if
        keyword db argument is absent or set to None.
        Default: True

    Returns
    -------
    text : str
        fulltext corresponding to the text_refs if it exists in the
        database, otherwise the abstract. Returns None if no content
        exists for the text_refs in the database
    """
    primary = False
    if open_db is None:
        open_db = get_primary_db
        primary = True
    if primary and use_cache:
        frozen_text_refs = frozenset(text_refs.items())
        result = _get_text_content_from_text_refs_cached(frozen_text_refs)
    else:
        with closing(open_db()) as db:
            text_ref_id = _get_text_ref_id_from_text_refs(text_refs, db)
            if text_ref_id is None:
                result = None
            else:
                result = _get_text_content_from_trid(text_ref_id, db)
    return result


@lru_cache(10000)
def _get_text_content_from_text_refs_cached(frozen_text_refs):
    with closing(get_primary_db()) as db:
        text_refs = dict(frozen_text_refs)
        text_ref_id = _get_text_ref_id_from_text_refs(text_refs, db)
        if text_ref_id is None:
            result = None
        else:
            result = _get_text_content_from_trid(text_ref_id, db)
    return result


def _get_text_ref_id_from_text_refs(text_refs, db):
    # In some cases the TRID is already there so we can just
    # return it
    if 'TRID' in text_refs:
        return text_refs['TRID']
    text_ref_id = None
    for id_type in ['pmid', 'pmcid', 'doi',
                    'pii', 'url', 'manuscript_id']:
        try:
            id_val = text_refs[id_type.upper()]
            trids = _get_trids(db, id_val, id_type)
            if trids:
                text_ref_id = trids[0]
                break
        except KeyError:
            pass
    return text_ref_id


def _get_text_content_from_trid(text_ref_id, db):
    texts = db.select_all([db.TextContent.content,
                           db.TextContent.text_type],
                          db.TextContent.text_ref_id == text_ref_id)
    contents = defaultdict(list)
    for content, text_type in texts:
        contents[text_type].append(content)
    # Look at text types in order of priority
    for text_type in ('fulltext', 'abstract', 'title'):
        # There are cases when we get a list of results for the same
        # content type with some that are None and some actual content,
        # so we iterate to find a non-empty content to return
        for content in contents.get(text_type, []):
            if content:
                return unpack(content)
    return None


def _extract_db_refs(stmt_json):
    agent_types = ['sub', 'subj', 'obj', 'enz', 'agent', 'gef;', 'ras',
                   'gap', 'obj_from', 'obj_to']
    db_ref_list = []

    for agent_type in agent_types:
        try:
            agent = stmt_json[agent_type]
        except KeyError:
            continue
        try:
            db_refs = agent['db_refs']
        except KeyError:
            continue
        db_ref_list.append(db_refs)

    members = stmt_json.get('members')
    if members is not None:
        for member in members:
            try:
                db_refs = member['db_refs']
            except KeyError:
                continue
            db_ref_list.append(db_refs)
    return db_ref_list
