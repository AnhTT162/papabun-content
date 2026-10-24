import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from papabun.content import Repo, split_layered, ContentError  # noqa: E402
from papabun.schema import SchemaValidator  # noqa: E402

LAYERED = "## Quick\n\nNhanh.\n\n## Interview\n\nPhỏng vấn.\n\n## Deep\n\nSâu.\n"


class Fixture:
    """Repo nội dung tối thiểu trong thư mục tạm, dùng schema thật của repo."""

    def __init__(self):
        self.root = Path(tempfile.mkdtemp())
        shutil.copytree(ROOT / "schema", self.root / "schema")
        self.write("tracks.json", {"schemaVersion": 1, "tracks": [
            {"id": "core-java", "order": 1, "title": "Core Java", "summary": "Java"}]})
        self.write("glossary.json", {"schemaVersion": 1, "terms": [
            {"id": "bucket", "term": "Bucket", "meaning": "Ô trong bảng băm."}]})
        self.write("project-questions.json", {"schemaVersion": 1, "technologies": []})
        self.topic_dir = self.root / "content" / "core-java" / "demo"
        self.topic = {
            "id": "demo", "schemaVersion": 1, "minAppVersion": "0.1", "track": "core-java",
            "title": "Demo", "level": "mid", "minutes": 5,
            "blocks": [{"type": "layered", "file": "layered.md"}],
        }
        self.write_topic()
        self.text("layered.md", LAYERED)

    def write(self, rel, data):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def write_topic(self):
        self.write("content/core-java/demo/topic.json", self.topic)

    def text(self, name, body):
        (self.topic_dir / name).write_text(body, encoding="utf-8")

    def errors(self):
        return Repo(self.root).validate()

    def cleanup(self):
        shutil.rmtree(self.root)


class SchemaValidatorTests(unittest.TestCase):
    def test_reports_missing_and_extra_fields(self):
        validator = SchemaValidator(ROOT / "schema")
        errors = validator.validate({"cards": [{"id": "Bad Id", "front": "", "extra": 1}]}, "flashcards.schema.json")
        joined = "\n".join(errors)
        self.assertIn("thiếu trường bắt buộc 'back'", joined)
        self.assertIn("trường không hợp lệ 'extra'", joined)
        self.assertIn("không được để trống", joined)
        self.assertIn("không khớp mẫu", joined)

    def test_booleans_are_not_integers(self):
        validator = SchemaValidator(ROOT / "schema")
        errors = validator.validate({"questions": [{
            "id": "q", "kind": "single", "prompt": "p", "options": ["a", "b"], "answer": True, "explanation": "e"}]},
            "quiz.schema.json")
        self.assertTrue(any("cần kiểu integer" in e for e in errors))

    def test_project_profile_schema(self):
        validator = SchemaValidator(ROOT / "schema")
        profile = {
            "schemaVersion": 1, "id": "payment-platform", "name": "Hệ thống thanh toán",
            "context": {"product": "Thanh toán cho sàn TMĐT", "scale": "~2.000 request/giây"},
            "role": "Backend lead", "techStack": [{"name": "Kafka", "technologyId": "kafka", "usage": "Event"}],
            "challenges": [{"title": "Trùng giao dịch", "situation": "S", "task": "T", "action": "A", "result": "R"}],
            "practiceQuestions": [{"id": "scale-10x", "text": "Traffic tăng 10 lần?"}],
        }
        self.assertEqual(validator.validate(profile, "project-profile.schema.json"), [])
        del profile["role"]
        self.assertTrue(validator.validate(profile, "project-profile.schema.json"))


class RepoValidationTests(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()

    def tearDown(self):
        self.fx.cleanup()

    def test_minimal_repo_is_valid(self):
        self.assertEqual(self.fx.errors(), [])

    def test_real_repo_is_valid(self):
        self.assertEqual(Repo(ROOT).validate(), [])

    def test_unknown_term_and_todo(self):
        self.fx.text("layered.md", LAYERED.replace("Nhanh.", "Xem [[hash-code]]. TODO"))
        errors = "\n".join(self.fx.errors())
        self.assertIn("[[hash-code]] chưa có trong glossary.json", errors)
        self.assertIn("còn chữ TODO", errors)

    def test_layered_needs_three_sections(self):
        self.fx.text("layered.md", "## Quick\n\nA\n\n## Deep\n\nB\n")
        self.assertTrue(any("## Quick, ## Interview, ## Deep" in e for e in self.fx.errors()))

    def test_id_must_match_folder_and_track_must_exist(self):
        self.fx.topic.update(id="other", track="spring")
        self.fx.write_topic()
        errors = "\n".join(self.fx.errors())
        self.assertIn("phải trùng tên thư mục", errors)
        self.assertIn("không có track 'spring'", errors)

    def test_missing_image(self):
        self.fx.text("layered.md", LAYERED.replace("Nhanh.", "![hình](images/a.png)"))
        self.assertTrue(any("không tìm thấy ảnh images/a.png" in e for e in self.fx.errors()))

    def test_quiz_answer_out_of_range(self):
        self.fx.write("content/core-java/demo/quiz.json", {"questions": [{
            "id": "q", "kind": "single", "prompt": "p", "options": ["a", "b"], "answer": 2, "explanation": "e"}]})
        self.assertTrue(any("answer vượt quá" in e for e in self.fx.errors()))

    def test_troubleshoot_graph_checks(self):
        self.fx.topic["blocks"].append({"type": "troubleshoot", "file": "t.json"})
        self.fx.write_topic()
        self.fx.write("content/core-java/demo/t.json", {"title": "T", "symptom": "S", "steps": [
            {"id": "start", "question": "?", "choices": [
                {"label": "a", "quality": "good", "feedback": "f", "next": "missing"}]},
            {"id": "orphan", "evidence": "e"}]})
        errors = "\n".join(self.fx.errors())
        self.assertIn("next 'missing' không tồn tại", errors)
        self.assertIn("step 'orphan' không thể đi tới", errors)

    def _curriculum(self, body):
        path = self.fx.root / "docs" / "CURRICULUM.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return "\n".join(self.fx.errors())

    def test_curriculum_must_list_written_topics_as_done(self):
        header = "### 2. Core Java (`core-java`)\n\n| # | id | Bài | Level | Trọng tâm | Block | |\n|---|---|---|---|---|---|---|\n"
        self.assertEqual(self._curriculum(header + "| 1 | `demo` | Demo | mid | x | L | ✅ |\n"), "")
        self.assertIn("còn đánh dấu ⬜", self._curriculum(header + "| 1 | `demo` | Demo | mid | x | L | ⬜ |\n"))
        self.assertIn("chưa có trong docs/CURRICULUM.md", self._curriculum(header + "| 1 | `other` | Khác | mid | x | L | ⬜ |\n"))
        wrong_track = header.replace("core-java", "jvm") + "| 1 | `demo` | Demo | mid | x | L | ✅ |\n"
        self.assertIn("track 'jvm'", self._curriculum(wrong_track))

    def test_diagram_references(self):
        self.fx.topic["blocks"].append({"type": "diagram", "file": "d.json"})
        self.fx.write_topic()
        self.fx.write("content/core-java/demo/d.json", {"title": "D",
            "nodes": [{"id": "a", "label": "A", "x": 0, "y": 0}],
            "edges": [{"id": "e", "from": "a", "to": "b"}],
            "steps": [{"caption": "c", "show": ["a", "zzz"]}]})
        errors = "\n".join(self.fx.errors())
        self.assertIn("không có node 'b'", errors)
        self.assertIn("không có node/edge 'zzz'", errors)

    def test_diagram_nodes_too_close_on_phone(self):
        self.fx.topic["blocks"].append({"type": "diagram", "file": "d.json"})
        self.fx.write_topic()
        self.fx.write("content/core-java/demo/d.json", {"title": "D",
            "nodes": [{"id": "a", "label": "A", "x": 0.1, "y": 0.5}, {"id": "b", "label": "B", "x": 0.25, "y": 0.6},
                      {"id": "c", "label": "C", "x": 0.2, "y": 0.1}],
            "edges": [], "steps": [{"caption": "c", "show": ["a", "b", "c"]}]})
        errors = "\n".join(self.fx.errors())
        self.assertIn("node 'a' và 'b' quá gần nhau", errors)
        self.assertNotIn("'a' và 'c'", errors)

    def test_diagram_rows_match_app_layout(self):
        # App coi chênh y < 0.35 là cùng hàng (thu nhỏ node); cùng cột thì chỉ lỗi khi chồng lên nhau.
        self.fx.topic["blocks"].append({"type": "diagram", "file": "d.json"})
        self.fx.write_topic()
        self.fx.write("content/core-java/demo/d.json", {"title": "D",
            "nodes": [{"id": "a", "label": "A", "x": 0.15, "y": 0.08}, {"id": "b", "label": "B", "x": 0.4, "y": 0.38},
                      {"id": "c", "label": "C", "x": 0.15, "y": 0.4}, {"id": "d", "label": "D", "x": 0.15, "y": 0.6}],
            "edges": [], "steps": [{"caption": "c", "show": ["a", "b", "c", "d"]}]})
        errors = "\n".join(self.fx.errors())
        self.assertIn("node 'a' và 'b' quá gần nhau", errors)
        self.assertNotIn("'a' và 'c'", errors)
        self.assertIn("node 'c' và 'd' quá gần nhau", errors)

    def _simulation(self, data):
        self.fx.topic["blocks"].append({"type": "simulation", "file": "sim.json"})
        self.fx.write_topic()
        self.fx.write("content/core-java/demo/sim.json", data)
        return "\n".join(self.fx.errors())

    def test_simulation_examples_are_valid(self):
        for example in sorted((ROOT / "schema" / "simulations" / "examples").glob("*.json")):
            data = json.loads(example.read_text(encoding="utf-8"))
            self.assertEqual(self._simulation(data), "", example.name)

    def test_thread_timeline_semantic_errors(self):
        data = json.loads((ROOT / "schema/simulations/examples/threadTimeline-lost-update.json").read_text(encoding="utf-8"))
        steps = data["config"]["threads"][0]["steps"]
        steps[0]["target"] = "missing"
        steps[1]["from"] = "nope"
        data["config"]["schedules"][0]["order"].append("t9")
        errors = self._simulation(data)
        self.assertIn("target phải là variable", errors)
        self.assertIn("from 'nope' chưa được read", errors)
        self.assertIn("không có thread 't9'", errors)

    def test_state_machine_semantic_errors(self):
        data = json.loads((ROOT / "schema/simulations/examples/stateMachine-circuit-breaker.json").read_text(encoding="utf-8"))
        data["config"]["initial"] = "ghost"
        data["config"]["transitions"][0]["to"] = "nowhere"
        data["config"]["events"].append({"id": "unused", "label": "X"})
        errors = self._simulation(data)
        self.assertIn("initial 'ghost'", errors)
        self.assertIn("không có state 'nowhere'", errors)
        self.assertIn("event 'unused' không được transition nào dùng", errors)

    def test_simulation_config_schema_errors(self):
        errors = self._simulation({"engine": "native:hashmap", "title": "H", "config": {"initialCapacity": 7, "keys": []}})
        self.assertIn("config.initialCapacity", errors)
        self.assertIn("config.keys: cần ít nhất 1", errors)

    def test_callout_rules(self):
        self.fx.topic["blocks"].append({"type": "callout", "file": "x.md"})
        self.fx.write_topic()
        errors = "\n".join(self.fx.errors())
        self.assertIn("thiếu 'style'", errors)
        self.assertIn("block inline không dùng 'file'", errors)


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()
        (self.fx.topic_dir / "images").mkdir()
        (self.fx.topic_dir / "images" / "map.png").write_bytes(b"\x89PNG fake")
        self.fx.text("layered.md", LAYERED.replace("Nhanh.", "![sơ đồ](images/map.png)"))
        self.out = self.fx.root / "dist"

    def tearDown(self):
        self.fx.cleanup()

    def build(self):
        repo = Repo(self.fx.root)
        self.assertEqual(repo.validate(), [])
        return repo.build(self.out, "v-test")

    def test_build_compiles_topic_and_images(self):
        manifest = self.build()
        names = {f["name"]: f for f in manifest["files"]}
        self.assertEqual(set(names), {"tracks.json", "glossary.json", "project-questions.json",
                                      "topic-demo.json", "img-demo-map.png"})
        self.assertEqual(names["topic-demo.json"]["minAppVersion"], "0.1")
        topic = json.loads((self.out / "topic-demo.json").read_text(encoding="utf-8"))
        self.assertEqual(topic["blocks"][0]["quick"], "![sơ đồ](img-demo-map.png)")
        self.assertEqual(topic["flashcards"], [])
        self.assertTrue((self.out / "img-demo-map.png").is_file())

    def test_build_is_deterministic(self):
        first = {f["name"]: f["sha256"] for f in self.build()["files"]}
        second = {f["name"]: f["sha256"] for f in self.build()["files"]}
        self.assertEqual(first, second)


class SplitLayeredTests(unittest.TestCase):
    def test_empty_section(self):
        with self.assertRaises(ContentError):
            split_layered("## Quick\n\n## Interview\n\nB\n\n## Deep\n\nC\n")


if __name__ == "__main__":
    unittest.main()
