"""Scrub rules for the public release. Synthetic strings only: no real narrative, no real name."""
from dmaic_planner import release as rel
from dmaic_planner.release import PERSON, scrub


def rules(s, action=None):
    return [f.rule for f in s.findings if action is None or f.action == action]


def test_a_name_in_parentheses_after_a_relation_word_is_replaced_and_so_are_its_repeats():
    s = scrub("Another coworker (Zorvan) walked in. Later the meeting with Zorvan ran long.")
    assert "Zorvan" not in s.text
    assert s.text == f"Another coworker ({PERSON}) walked in. Later the meeting with {PERSON} ran long."
    assert rules(s, "replaced") == ["relation-name", "repeat"]


def test_a_given_name_after_a_relation_word_is_replaced_but_an_unknown_word_is_only_flagged():
    s = scrub("My manager Alice moved the meeting again.")
    assert s.text == f"My manager {PERSON} moved the meeting again."
    s = scrub("My manager Quexley moved the meeting again.")
    assert s.text == "My manager Quexley moved the meeting again."
    assert rules(s, "needs_review") == ["relation-name"]


def test_lists_and_proper_nouns_after_a_relation_word_are_not_names():
    for text in ("The hierarchy is CEO, GM, Sales Manager, Estimators.",
                 "A Patient Safety Authority analyst read the report.",
                 "We will file with the Attorney General office."):
        s = scrub(text)
        assert s.text == text and not s.findings, text


def test_title_keeps_the_title_and_replaces_the_name():
    s = scrub("Dr. Examplar ordered the test and Mrs. Testerson signed.")
    assert s.text == f"Dr. {PERSON} ordered the test and Mrs. {PERSON} signed."
    assert set(rules(s, "replaced")) == {"title-name"}


def test_full_name_from_a_common_given_name_and_a_surname():
    s = scrub("The ticket was opened by Alice Fictionalia yesterday.")
    assert s.text == f"The ticket was opened by {PERSON} yesterday."


def test_a_given_name_on_its_own_is_flagged_not_changed():
    s = scrub("We asked Alice for the logs.")
    assert s.text == "We asked Alice for the logs."
    assert rules(s, "needs_review") == ["given-name"]


def test_signature_after_a_sign_off():
    s = scrub("Please fix the export.\nRegards,\nAlice\n")
    assert s.text == f"Please fix the export.\nRegards,\n{PERSON}\n"


def test_help_desk_greetings_are_not_signatures():
    text = "Check the attached logs regards\n\nDears [user] please update\n\nGreetings any update. Regards"
    s = scrub(text)
    assert s.text == text and not s.findings


def test_email_phone_and_handle_are_replaced_but_a_time_after_at_is_not():
    s = scrub("Write to someone@example.com or call 555-010-1234, ping @devhandle99, meet @ 11 am.")
    assert s.text == "Write to [email] or call [phone], ping [handle], meet @ 11 am."
    assert set(rules(s, "replaced")) == {"email", "phone", "handle"}


def test_long_numbers_use_the_validate_raw_patterns():
    s = scrub("Account 123456789012 and SSN 123-45-6789 were exposed.")
    assert s.text == "Account [number] and SSN [number] were exposed."


def test_known_issue16_names_are_replaced_case_insensitively():
    s = scrub("Thanks to zorkfiction99 and to Qwyn Fictional for the answer.",
              known_names=("Zorkfiction99", "Qwyn Fictional"))
    assert s.text == f"Thanks to {PERSON} and to {PERSON} for the answer."
    assert rules(s, "replaced") == ["issue16-author", "issue16-author"]


def test_organizations_that_look_like_people_are_kept():
    text = "Loans backed by Freddie Mac and Fannie Mae were sold to Charles Schwab clients."
    s = scrub(text)
    assert s.text == text and not s.findings


def test_case_citations_and_surname_firms_are_flagged_not_changed():
    text = "See Examplar v. Testerson. The debt went to Ableson, Bakerson & Carterson for collection."
    s = scrub(text)
    assert s.text == text
    assert rules(s, "needs_review") == ["case-citation", "surname-firm"]


def test_a_government_report_keeps_officials_for_review():
    text = "Mr. Examplar, the agency official, said the backlog grew."
    s = scrub(text, government=True)
    assert s.text == text
    assert rules(s, "needs_review") == ["title-name"]
    assert "government report" in s.findings[0].note


def test_review_decisions_keep_or_replace_a_flagged_span():
    text = "See Examplar v. Testerson."
    kept = scrub(text, decisions={"Examplar v. Testerson": "keep"})
    assert kept.text == text and [f.action for f in kept.findings] == ["kept"]
    gone = scrub(text, decisions={"Examplar v. Testerson": "[case citation]"})
    assert gone.text == "See [case citation]."


def test_scrub_is_deterministic_and_a_second_pass_finds_nothing_to_replace():
    text = "My manager Alice emailed alice.x@example.com; coworker (Zorvan) agreed with Alice."
    first, again = scrub(text), scrub(text)
    assert first == again
    assert not scrub(first.text).replaced


def test_stack_exchange_license_follows_the_post_date():
    assert rel.se_license("2011-03-16") == "CC BY-SA 2.5"
    assert rel.se_license("2014-01-27") == "CC BY-SA 3.0"
    assert rel.se_license("2019-09-27") == "CC BY-SA 4.0"


SE_RAW = {"notes": "question_id=7; author=Exampleuser42; "
                   "author_url=https://pm.stackexchange.com/users/9/exampleuser42; created=2019-01-01",
          "storage_mode": "verbatim"}
SE_URL = "https://pm.stackexchange.com/questions/7/a-synthetic-question"


def test_stack_exchange_attribution_names_the_author_and_profile_by_default():
    p = rel.provenance("SE-0001", SE_RAW, SE_URL)
    assert p["attribution"] == ("Question 7 on pm.stackexchange.com, asked 2019-01-01, by Exampleuser42 "
                                "(https://pm.stackexchange.com/users/9/exampleuser42)")
    assert p["license"] == "CC BY-SA 4.0" and p["source"] == "Stack Exchange: pm.stackexchange.com"
    off = rel.provenance("SE-0001", SE_RAW, SE_URL, with_se_authors=False)
    assert "Exampleuser42" not in off["attribution"] and "question page" in off["attribution"]


def test_csv_is_replaced_whole_and_leaves_no_temp_file(tmp_path):
    path = tmp_path / "train.csv"
    rel.write_csv(path, ["id", "text"], [{"id": "a", "text": "old"}])
    rel.write_csv(path, ["id", "text"], [{"id": "a", "text": "new,\nwith a line break"}])
    assert rel.read_csv(path) == [{"id": "a", "text": "new,\nwith a line break"}]
    assert [p.name for p in tmp_path.iterdir()] == ["train.csv"]


def test_context_marks_the_span_on_one_line():
    text = "first line\nmy manager Alice said\nthird line"
    s = scrub(text)
    ctx = rel.context(text, s.findings[0])
    assert "«Alice»" in ctx and "\n" not in ctx
