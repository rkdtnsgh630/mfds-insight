import io
import json
import sqlite3
import unittest
import urllib.error

from collector import client as C
from collector import store as S
from collector.apis import APIS, select_apis
from collector.run import collect_api


def ok_json(items, total=None):
    return json.dumps({"header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
                       "body": {"pageNo": 1, "numOfRows": 10,
                                "totalCount": len(items) if total is None else total, "items": items}})


class ParseTests(unittest.TestCase):
    def test_normalize_items_shapes(self):
        self.assertEqual(C.normalize_items([{"A": 1}]), [{"A": 1}])
        self.assertEqual(C.normalize_items([{"item": {"A": 1}}]), [{"A": 1}])
        self.assertEqual(C.normalize_items({"item": [{"A": 1}, {"A": 2}]}), [{"A": 1}, {"A": 2}])
        self.assertEqual(C.normalize_items({"item": {"A": 1}}), [{"A": 1}])
        self.assertEqual(C.normalize_items(""), [])
        self.assertEqual(C.normalize_items(None), [])

    def test_parse_json(self):
        code, msg, total, items = C.parse_response(ok_json([{"ITEM_SEQ": "1"}], total=42))
        self.assertEqual((code, total, items), ("00", 42, [{"ITEM_SEQ": "1"}]))

    def test_parse_json_response_wrapper(self):
        text = json.dumps({"response": {"header": {"resultCode": "00"},
                                        "body": {"totalCount": "2", "items": {"item": [{"A": 1}, {"A": 2}]}}}})
        self.assertEqual(C.parse_response(text)[2:], (2, [{"A": 1}, {"A": 2}]))

    def test_parse_xml(self):
        xml = ("<response><header><resultCode>00</resultCode><resultMsg>OK</resultMsg></header>"
               "<body><totalCount>1</totalCount><items><item><ITEM_SEQ>9</ITEM_SEQ></item></items></body></response>")
        self.assertEqual(C.parse_response(xml), ("00", "OK", 1, [{"ITEM_SEQ": "9"}]))

    def test_portal_error(self):
        body = json.dumps({"OpenAPI_ServiceResponse": {"cmmMsgHeader": {
            "errMsg": "SERVICE_KEY_IS_NOT_REGISTERED_ERROR", "returnAuthMsg": "x", "returnReasonCode": "30"}}})
        with self.assertRaises(C.ApiError) as cm:
            C.parse_response(body)
        self.assertEqual(cm.exception.code, "30")

    def test_normalize_key(self):
        self.assertEqual(C.normalize_key(" a%2Bb%2Fc%3D%3D "), "a+b/c==")
        self.assertEqual(C.normalize_key("a+b/c=="), "a+b/c==")


class ClientTests(unittest.TestCase):
    def test_403_portal_error_not_retried(self):
        calls = []
        body = json.dumps({"OpenAPI_ServiceResponse": {"cmmMsgHeader": {
            "errMsg": "SERVICE_KEY_IS_NOT_REGISTERED_ERROR", "returnAuthMsg": "x", "returnReasonCode": "30"}}})

        def opener(req, timeout):
            calls.append(1)
            raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, io.BytesIO(body.encode()))

        c = C.Client("secret+key/==", opener=opener, sleeper=lambda s: None)
        with self.assertRaises(C.ApiError) as cm:
            c.get_page("X/y", 1, 10)
        self.assertEqual(cm.exception.code, "30")
        self.assertEqual(len(calls), 1)
        self.assertNotIn("secret", str(cm.exception))

    def test_retry_then_success(self):
        state = {"n": 0}

        def opener(req, timeout):
            state["n"] += 1
            if state["n"] == 1:
                raise urllib.error.URLError("temporary")
            return io.BytesIO(ok_json([{"A": 1}]).encode())

        c = C.Client("k", opener=opener, sleeper=lambda s: None)
        self.assertEqual(c.get_page("X/y", 1, 10), (1, [{"A": 1}]))
        self.assertEqual(state["n"], 2)

    def test_key_is_url_encoded(self):
        seen = {}

        def opener(req, timeout):
            seen["url"] = req.full_url
            return io.BytesIO(ok_json([]).encode())

        C.Client("a+b/c==", opener=opener, sleeper=lambda s: None).get_page("S/op", 2, 50)
        self.assertIn("serviceKey=a%2Bb%2Fc%3D%3D", seen["url"])
        self.assertIn("pageNo=2", seen["url"])
        self.assertIn("type=json", seen["url"])


class FakeClient:
    key = "fake"

    def __init__(self, pages):
        self.pages = pages
        self.calls = 0

    def get_page(self, path, page_no, rows):
        self.calls += 1
        items = self.pages[page_no - 1] if page_no - 1 < len(self.pages) else []
        return sum(len(p) for p in self.pages), items


API = {"id": "t", "name": "test", "data_id": "0", "path": "T/t", "key": ["ID"], "tier": "core"}


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.con = S.connect(":memory:")

    def run_once(self, pages, rows=2, max_pages=None, api=API):
        run_id = S.start_run(self.con, "test", "t")
        return collect_api(self.con, FakeClient(pages), run_id, api, rows, max_pages)

    def changes(self):
        return [r[0] for r in self.con.execute("SELECT change_type FROM change_log ORDER BY id")]

    def test_baseline_then_changes_then_guard(self):
        r1 = self.run_once([[{"ID": 1, "v": "a"}, {"ID": 2, "v": "b"}], [{"ID": 3, "v": "c"}]])
        self.assertEqual((r1["status"], r1["added"]), ("complete", 3))
        self.assertIn("기준선", r1["note"])
        self.assertEqual(self.changes(), [])

        r2 = self.run_once([[{"ID": 1, "v": "a2"}, {"ID": 3, "v": "c"}], [{"ID": 4, "v": "d"}]])
        self.assertEqual((r2["updated"], r2["added"], r2["removed"]), (1, 1, 1))
        self.assertEqual(sorted(self.changes()), ["added", "removed", "updated"])
        present = self.con.execute("SELECT record_key FROM raw_record WHERE is_present=0").fetchall()
        self.assertEqual(present, [("2",)])

        r3 = self.run_once([[{"ID": 1, "v": "a2"}]])
        self.assertEqual(r3["removed"], 0)
        self.assertIn("보류", r3["note"])

    def test_reappeared(self):
        self.run_once([[{"ID": 1}, {"ID": 2}], [{"ID": 3}]])
        self.run_once([[{"ID": 1}, {"ID": 2}]])  # ID 3 결측 (2/3 >= 50%)
        r = self.run_once([[{"ID": 1}, {"ID": 2}], [{"ID": 3}]])
        self.assertEqual(r["reappeared"], 1)
        self.assertEqual(self.changes()[-1], "reappeared")

    def test_key_collision_and_duplicates(self):
        r = self.run_once([[{"ID": 1, "v": "a"}, {"ID": 1, "v": "b"}], [{"ID": 1, "v": "a"}]])
        self.assertEqual((r["key_collisions"], r["duplicates"]), (1, 1))
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM raw_record").fetchone()[0], 2)

    def test_hash_key_when_no_key_fields(self):
        api = dict(API, id="h", key=None)
        self.run_once([[{"A": 1}, {"A": 2}]], api=api)
        keys = [k for (k,) in self.con.execute("SELECT record_key FROM raw_record WHERE api_id='h'")]
        self.assertTrue(all(k.startswith("h:") for k in keys))

    def test_partial_run_does_not_mark_removed(self):
        self.run_once([[{"ID": 1}, {"ID": 2}], [{"ID": 3}]])
        r = self.run_once([[{"ID": 1}, {"ID": 2}], [{"ID": 3}]], max_pages=1)
        self.assertEqual((r["status"], r["removed"]), ("partial", 0))
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM raw_record WHERE is_present=0").fetchone()[0], 0)

    def test_api_error_recorded(self):
        class Failing(FakeClient):
            def get_page(self, path, page_no, rows):
                raise C.ApiError("SERVICE_KEY_IS_NOT_REGISTERED_ERROR", code="30")

        run_id = S.start_run(self.con, "test", "t")
        r = collect_api(self.con, Failing([]), run_id, API, 2)
        self.assertEqual(r["status"], "failed")
        self.assertIn("[30]", r["error"])


class RegistryTests(unittest.TestCase):
    def test_ids_unique_and_selection(self):
        ids = [a["id"] for a in APIS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(a["tier"] == "core" for a in select_apis("tier:core")))
        self.assertEqual([a["id"] for a in select_apis("tier:slow")], ["drug_permit_detail"])
        self.assertEqual(len(select_apis("tier:core+slow")), 11)
        self.assertEqual([a["id"] for a in select_apis("gmp,dmf")], ["gmp", "dmf"])
        with self.assertRaises(ValueError):
            select_apis("nope")


if __name__ == "__main__":
    unittest.main()
