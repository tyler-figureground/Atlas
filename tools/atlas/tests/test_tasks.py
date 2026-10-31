"""Task-line parser (core.tasks): one parse for the digest, the queue and archive."""

from __future__ import annotations

from datetime import date

from atlas.core.tasks import parse_open

TASKS_MD = """# Tasks - Test

## In progress

- [ ] T-010 `MODEL` Repair the A501 schedules - claimed 2026-10-04 by pi

## Now

- [ ] T-011 `DECISION` Choose the stair nosing profile - added:2026-10-01 due:2026-11-05
- [ ] **T-012** `AGENT` Draft the egress memo - after:T-011 after:T-014
- [ ] T-013 `MODEL` Place the stair - after:T-011, T-099
- [x] T-002 `AGENT` Closed already - after:T-011

## Next

- [ ] T-014 `DECISION` Approve the allowance basis.

## Done

- [ ] T-001 `DECISION` Under Done never counts - after:T-014
"""


def test_open_items_before_done_with_lane_filter():
    items = parse_open(TASKS_MD)
    assert [i.id for i in items] == ["T-010", "T-011", "T-012", "T-013", "T-014"]
    assert [i.id for i in parse_open(TASKS_MD, lane="DECISION")] == ["T-011", "T-014"]
    assert items[0].lane == "MODEL" and items[0].section == "In progress"
    assert items[0].claim == "claimed 2026-10-04 by pi"


def test_tokens_due_added_after():
    by_id = {i.id: i for i in parse_open(TASKS_MD)}
    assert by_id["T-011"].added == date(2026, 10, 1)
    assert by_id["T-011"].due == date(2026, 11, 5)
    assert by_id["T-012"].after == ("T-011", "T-014")  # bold id still parsed
    assert by_id["T-013"].after == ("T-011", "T-099")  # comma list after one token
    assert by_id["T-014"].after == () and by_id["T-014"].due is None


def test_ready_and_source_date():
    text = "\n".join([
        "## Now",
        "- [ ] Y-003 Email the survey. ready: 07 Correspondence/_Outbox/261005_survey.md",
        "- [ ] Y-004 Review the list - from [minutes](../11%20Meetings/261021%20-%20Site%20Visit.md).",
        "- [ ] Y-005 Buy the screen (Elite ELECTRIC100H) - part 260117 is not a date link.",
        "- [ ] Y-006 Call back - added:2026-10-20 from [minutes](../11%20Meetings/261001%20-%20X.md)",
        "- [ ] Y-007 Bad token due:2026-13-40 stays undated.",
    ])
    items = {i.id: i for i in parse_open(text)}
    assert items["Y-003"].ready == "07 Correspondence/_Outbox/261005_survey.md"
    assert items["Y-003"].source_date == date(2026, 10, 5)  # YYMMDD file the line links
    assert items["Y-004"].ready == "" and items["Y-004"].source_date == date(2026, 10, 21)
    assert items["Y-005"].source_date is None  # bare digits outside a link never date a line
    assert items["Y-006"].since == date(2026, 10, 20)  # added: outranks the link date
    assert items["Y-007"].due is None


def test_age_is_unknown_without_a_date():
    item = parse_open("## Now\n- [ ] Y-001 Call the engineer.\n")[0]
    assert item.since is None and item.age_days(date(2026, 10, 31)) is None
    dated = parse_open("## Now\n- [ ] Y-002 Call - added:2026-10-21\n")[0]
    assert dated.age_days(date(2026, 10, 31)) == 10


def test_text_is_clipped_but_tokens_read_from_the_full_line():
    long = "- [ ] Y-001 " + "word " * 60 + "due:2026-11-01"
    item = parse_open("## Now\n" + long + "\n")[0]
    assert len(item.text) <= 160 and item.text.endswith("…")
    assert item.due == date(2026, 11, 1)


def test_review_round_parser_edges():
    lines = "\n".join([
        "## Now",
        # ready: as a bare path followed by tokens stops before the tokens
        "- [ ] Y-010 Send the letter. ready: 07 Correspondence/_Outbox/261001_letter.md added:2026-10-02 due:2026-11-01",
        # angle-bracket CommonMark link, spaces unencoded
        "- [ ] Y-011 Send the request. ready: [draft](<../08 OUT/Drafts/261008_Request.md>).",
        # the file's own date wins over a dated project folder higher in the path
        "- [ ] Y-012 Review - [m](G:/Drive/250101_Foo/11%20Meetings/261015%20-%20Minutes.md)",
        # prose 'ready:' is not an artifact
        "- [ ] Y-013 Check whether the permit is ready: call DOB.",
        # claim stops before tokens
        "- [ ] T-020 `AGENT` Draft memo - claimed 2026-10-30 by codex added:2026-10-02",
        # a future added: date is a typo, not a negative age
        "- [ ] Y-014 Call back - added:2026-12-25",
        # after: ids normalise, so T-7 names T-007
        "- [ ] T-021 `MODEL` Place it - after:T-7",
    ])
    items = {i.id: i for i in parse_open(lines)}
    assert items["Y-010"].ready == "07 Correspondence/_Outbox/261001_letter.md"
    assert items["Y-010"].added == date(2026, 10, 2) and items["Y-010"].due == date(2026, 11, 1)
    assert items["Y-011"].ready == "../08 OUT/Drafts/261008_Request.md"
    assert items["Y-011"].source_date == date(2026, 10, 8)
    assert items["Y-012"].source_date == date(2026, 10, 15)
    assert items["Y-013"].ready == ""
    assert items["T-020"].claim == "claimed 2026-10-30 by codex"
    assert items["Y-014"].age_days(date(2026, 10, 31)) is None
    assert items["T-021"].after == ("T-007",)
