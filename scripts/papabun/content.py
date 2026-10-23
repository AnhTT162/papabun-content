"""Đọc, kiểm tra và biên dịch nội dung PapaBun.

Định dạng nguồn (repo) và định dạng phát hành (dist/) được mô tả trong README.md.
"""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .schema import SchemaValidator

MANIFEST_SCHEMA_VERSION = 1

TERM_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
IMAGE_RE = re.compile(r"\]\((images/[^)\s]+)\)")
IMAGE_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+\.(png|jpg|jpeg|gif|svg|webp)$")
LAYERED_SECTIONS = ["Quick", "Interview", "Deep"]
# Khớp với DiagramLayout trong app (node cao 52pt, khung 300pt, node rộng tối thiểu 56pt).
DIAGRAM_ROW = 0.25
DIAGRAM_MIN_DX = 0.24
DIAGRAM_MAX_LABEL = 20
SIMULATION_SCHEMAS = {
    "threadTimeline": "simulations/threadTimeline.schema.json",
    "stateMachine": "simulations/stateMachine.schema.json",
    "native:hashmap": "simulations/native-hashmap.schema.json",
}

# type -> (đuôi file yêu cầu, schema của file). None: block inline.
FILE_BLOCKS = {
    "analogy": (".md", None),
    "layered": (".md", None),
    "breakLab": (".json", "blocks/lab.schema.json"),
    "scenario": (".json", "blocks/scenario.schema.json"),
    "troubleshoot": (".json", "blocks/troubleshoot.schema.json"),
    "diagram": (".json", "blocks/diagram.schema.json"),
    "simulation": (".json", "blocks/simulation.schema.json"),
    "code": (None, None),
}
INLINE_BLOCKS = {"callout"}


class ContentError(Exception):
    pass


class Topic:
    def __init__(self, folder, meta):
        self.folder = folder
        self.meta = meta

    @property
    def id(self):
        return self.meta.get("id")


class Repo:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.validator = SchemaValidator(self.root / "schema")
        self.errors = []
        self.tracks = self._load_json("tracks.json", "tracks.schema.json") or {"tracks": []}
        self.glossary = self._load_json("glossary.json", "glossary.schema.json") or {"terms": []}
        self.project_questions = (
            self._load_json("project-questions.json", "project-questions.schema.json")
            or {"technologies": []}
        )
        self.topics = []
        for topic_file in sorted((self.root / "content").glob("*/*/topic.json")):
            meta = self._load_json(topic_file, "topic.schema.json")
            if meta is not None:
                self.topics.append(Topic(topic_file.parent, meta))

    # ---------- tiện ích ----------

    def rel(self, path):
        return str(Path(path).resolve().relative_to(self.root))

    def error(self, path, message):
        self.errors.append("%s: %s" % (self.rel(path), message))

    def _load_json(self, path, schema_name):
        path = self.root / path
        if not path.exists():
            self.error(path, "không tìm thấy file")
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            self.error(path, "JSON không hợp lệ (%s)" % exc)
            return None
        problems = self.validator.validate(data, schema_name)
        for problem in problems:
            self.error(path, problem)
        return None if problems else data

    def _read_text(self, path):
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            self.error(path, "không tìm thấy file")
            return None

    # ---------- kiểm tra ----------

    def validate(self):
        """Kiểm tra toàn bộ repo. Trả về danh sách lỗi (rỗng nghĩa là hợp lệ)."""
        track_ids = self._unique([t["id"] for t in self.tracks["tracks"]], self.root / "tracks.json", "track")
        self._unique([t["order"] for t in self.tracks["tracks"]], self.root / "tracks.json", "order của track")
        term_ids = self._unique([t["id"] for t in self.glossary["terms"]], self.root / "glossary.json", "thuật ngữ")
        topic_ids = self._unique([t.id for t in self.topics], self.root / "content", "topic")

        for term in self.glossary["terms"]:
            for ref in term.get("related", []):
                if ref not in term_ids:
                    self.error(self.root / "glossary.json", "%s.related: không có thuật ngữ '%s'" % (term["id"], ref))
            for ref in term.get("topics", []):
                if ref not in topic_ids:
                    self.error(self.root / "glossary.json", "%s.topics: không có topic '%s'" % (term["id"], ref))
            self._check_text(term["meaning"], self.root / "glossary.json", term_ids)

        pq_path = self.root / "project-questions.json"
        self._unique([t["id"] for t in self.project_questions["technologies"]], pq_path, "công nghệ")
        for tech in self.project_questions["technologies"]:
            self._unique([q["id"] for q in tech["questions"]], pq_path, "câu hỏi trong %s" % tech["id"])
            for ref in tech.get("topics", []):
                if ref not in topic_ids:
                    self.error(pq_path, "%s.topics: không có topic '%s'" % (tech["id"], ref))

        for topic in self.topics:
            self._validate_topic(topic, track_ids, topic_ids, term_ids)
        self.errors = list(dict.fromkeys(self.errors))
        return self.errors

    def _unique(self, values, path, label):
        seen = set()
        for value in values:
            if value in seen:
                self.error(path, "%s '%s' bị trùng" % (label, value))
            seen.add(value)
        return seen

    def _check_text(self, text, path, term_ids, folder=None):
        if "TODO" in text:
            self.error(path, "còn chữ TODO chưa viết xong")
        for term in TERM_RE.findall(text):
            if term not in term_ids:
                self.error(path, "thuật ngữ [[%s]] chưa có trong glossary.json" % term)
        for image in IMAGE_RE.findall(text):
            if folder is None:
                self.error(path, "chỉ dùng được ảnh trong nội dung topic: %s" % image)
            elif not IMAGE_NAME_RE.match(Path(image).name):
                self.error(path, "tên ảnh không hợp lệ: %s" % image)
            elif not (folder / image).is_file():
                self.error(path, "không tìm thấy ảnh %s" % image)

    def _validate_topic(self, topic, track_ids, topic_ids, term_ids):
        meta, folder = topic.meta, topic.folder
        path = folder / "topic.json"

        if meta["id"] != folder.name:
            self.error(path, "id '%s' phải trùng tên thư mục '%s'" % (meta["id"], folder.name))
        if meta["track"] != folder.parent.name:
            self.error(path, "track '%s' phải trùng thư mục cha '%s'" % (meta["track"], folder.parent.name))
        if meta["track"] not in track_ids:
            self.error(path, "không có track '%s' trong tracks.json" % meta["track"])
        for ref in meta.get("prerequisites", []):
            if ref == meta["id"] or ref not in topic_ids:
                self.error(path, "prerequisites: topic '%s' không hợp lệ" % ref)
        for ref in meta.get("terms", []):
            if ref not in term_ids:
                self.error(path, "terms: thuật ngữ '%s' chưa có trong glossary.json" % ref)
        for value in _strings(meta):
            self._check_text(value, path, term_ids, folder)

        for index, block in enumerate(meta["blocks"]):
            self._validate_block(topic, index, block, term_ids)

        cards = self._load_optional(folder / "flashcards.json", "flashcards.schema.json")
        if cards:
            self._unique([c["id"] for c in cards["cards"]], folder / "flashcards.json", "flashcard")
            for value in _strings(cards):
                self._check_text(value, folder / "flashcards.json", term_ids, folder)

        quiz = self._load_optional(folder / "quiz.json", "quiz.schema.json")
        if quiz:
            self._unique([q["id"] for q in quiz["questions"]], folder / "quiz.json", "câu quiz")
            for q in quiz["questions"]:
                if q["answer"] >= len(q["options"]):
                    self.error(folder / "quiz.json", "%s: answer vượt quá số lựa chọn" % q["id"])
            for value in _strings(quiz):
                self._check_text(value, folder / "quiz.json", term_ids, folder)

    def _load_optional(self, path, schema_name):
        return self._load_json(path, schema_name) if path.exists() else None

    def _validate_block(self, topic, index, block, term_ids):
        path = topic.folder / "topic.json"
        label = "blocks[%d] (%s)" % (index, block["type"])
        kind = block["type"]

        if kind in INLINE_BLOCKS:
            for key in ("style", "markdown"):
                if key not in block:
                    self.error(path, "%s: thiếu '%s'" % (label, key))
            for key in ("file", "caption"):
                if key in block:
                    self.error(path, "%s: block inline không dùng '%s'" % (label, key))
            return

        for key in ("style", "markdown"):
            if key in block:
                self.error(path, "%s: '%s' chỉ dùng cho callout" % (label, key))
        if "caption" in block and kind != "code":
            self.error(path, "%s: 'caption' chỉ dùng cho code" % label)
        if "file" not in block:
            self.error(path, "%s: thiếu 'file'" % label)
            return

        extension, schema_name = FILE_BLOCKS[kind]
        file_path = topic.folder / block["file"]
        if extension and file_path.suffix != extension:
            self.error(path, "%s: file phải có đuôi %s" % (label, extension))
            return

        if schema_name:
            data = self._load_json(file_path, schema_name)
            if data is None:
                return
            for value in _strings(data):
                self._check_text(value, file_path, term_ids, topic.folder)
            check = getattr(self, "_check_" + kind, None)
            if check:
                check(file_path, data)
            return

        text = self._read_text(file_path)
        if text is None:
            return
        self._check_text(text, file_path, term_ids, topic.folder)
        if kind == "layered":
            try:
                split_layered(text)
            except ContentError as exc:
                self.error(file_path, str(exc))

    def _check_breakLab(self, path, data):
        diagnosis = data["diagnosis"]
        if diagnosis["answer"] >= len(diagnosis["options"]):
            self.error(path, "diagnosis.answer vượt quá số lựa chọn")

    def _check_troubleshoot(self, path, data):
        steps = {s["id"]: s for s in data["steps"]}
        self._unique([s["id"] for s in data["steps"]], path, "step")
        for step in data["steps"]:
            choices = step.get("choices", [])
            if choices and "question" not in step:
                self.error(path, "step '%s' có choices nhưng thiếu question" % step["id"])
            if not choices and "evidence" not in step:
                self.error(path, "step kết luận '%s' cần evidence" % step["id"])
            for choice in choices:
                if choice["next"] not in steps:
                    self.error(path, "step '%s': next '%s' không tồn tại" % (step["id"], choice["next"]))
        if all(s.get("choices") for s in data["steps"]):
            self.error(path, "cần ít nhất một step kết luận (không có choices)")
        reachable, queue = set(), [data["steps"][0]["id"]]
        while queue:
            current = queue.pop()
            if current in reachable or current not in steps:
                continue
            reachable.add(current)
            queue.extend(c["next"] for c in steps[current].get("choices", []))
        for step_id in steps:
            if step_id not in reachable:
                self.error(path, "step '%s' không thể đi tới từ bước đầu" % step_id)

    def _check_simulation(self, path, data):
        engine = data["engine"]
        schema_name = SIMULATION_SCHEMAS[engine]
        problems = self.validator.validate(data["config"], schema_name)
        for problem in problems:
            self.error(path, "config: " + problem.replace("$", "config", 1))
        if problems:
            return
        getattr(self, "_check_" + engine.replace("native:", "native_"))(path, data["config"])

    def _check_threadTimeline(self, path, config):
        kinds = {r["id"]: r["kind"] for r in config["resources"]}
        self._unique([r["id"] for r in config["resources"]], path, "resource")
        thread_ids = self._unique([t["id"] for t in config["threads"]], path, "thread")
        for resource in config["resources"]:
            if resource["kind"] == "lock" and set(resource) & {"valueType", "initial", "volatile"}:
                self.error(path, "resource '%s': lock không dùng valueType/initial/volatile" % resource["id"])
        needs = {"lock": "lock", "unlock": "lock", "read": "variable", "write": "variable", "spinUntil": "variable"}
        for thread in config["threads"]:
            locals_ = set()
            for i, step in enumerate(thread["steps"]):
                where = "thread '%s' steps[%d] (%s)" % (thread["id"], i, step["op"])
                op = step["op"]
                if op in needs:
                    target = step.get("target")
                    if kinds.get(target) != needs[op]:
                        self.error(path, "%s: target phải là %s có trong resources" % (where, needs[op]))
                elif "target" in step:
                    self.error(path, "%s: work không dùng target" % where)
                if op == "read":
                    if "into" not in step:
                        self.error(path, "%s: thiếu into" % where)
                    locals_.add(step.get("into"))
                if op == "write" and ("value" in step) == ("from" in step):
                    self.error(path, "%s: cần đúng một trong value hoặc from" % where)
                if op == "write" and "from" in step and step["from"] not in locals_:
                    self.error(path, "%s: from '%s' chưa được read trước đó trong thread" % (where, step["from"]))
                if op == "spinUntil" and "value" not in step:
                    self.error(path, "%s: thiếu value" % where)
        for schedule in config.get("schedules", []):
            for ref in schedule["order"]:
                if ref not in thread_ids:
                    self.error(path, "schedule '%s': không có thread '%s'" % (schedule["id"], ref))
        for item in config.get("expect", []):
            if kinds.get(item["target"]) != "variable":
                self.error(path, "expect: '%s' không phải variable" % item["target"])

    def _check_stateMachine(self, path, config):
        state_ids = self._unique([s["id"] for s in config["states"]], path, "state")
        event_ids = self._unique([e["id"] for e in config["events"]], path, "event")
        counter_ids = self._unique([c["id"] for c in config.get("counters", [])], path, "counter")
        self._unique([t["id"] for t in config["transitions"]], path, "transition")
        if config["initial"] not in state_ids:
            self.error(path, "initial '%s' không có trong states" % config["initial"])
        used_events = set()
        for t in config["transitions"]:
            for end in ("from", "to"):
                if t[end] not in state_ids:
                    self.error(path, "transition '%s'.%s: không có state '%s'" % (t["id"], end, t[end]))
            if t["event"] not in event_ids:
                self.error(path, "transition '%s': không có event '%s'" % (t["id"], t["event"]))
            used_events.add(t["event"])
            refs = ([t["guard"]] if "guard" in t else []) + t.get("effects", [])
            for ref in refs:
                if ref["counter"] not in counter_ids:
                    self.error(path, "transition '%s': không có counter '%s'" % (t["id"], ref["counter"]))
        for event in event_ids - used_events:
            self.error(path, "event '%s' không được transition nào dùng" % event)
        self._check_spacing(path, config["states"])

    def _check_native_hashmap(self, path, config):
        self._unique(config["keys"], path, "key")

    def _check_spacing(self, path, nodes):
        # Trên điện thoại khung sơ đồ chỉ rộng ~340pt: hai node cùng hàng cần cách nhau đủ xa.
        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                if abs(a["y"] - b["y"]) < DIAGRAM_ROW and abs(a["x"] - b["x"]) < DIAGRAM_MIN_DX:
                    self.error(path, "node '%s' và '%s' quá gần nhau: cùng hàng (|y| chênh < %.2f) thì x phải chênh >= %.2f"
                               % (a["id"], b["id"], DIAGRAM_ROW, DIAGRAM_MIN_DX))

    def _check_diagram(self, path, data):
        node_ids = self._unique([n["id"] for n in data["nodes"]], path, "node")
        edge_ids = self._unique([e["id"] for e in data["edges"]], path, "edge")
        for edge in data["edges"]:
            for end in ("from", "to"):
                if edge[end] not in node_ids:
                    self.error(path, "edge '%s'.%s: không có node '%s'" % (edge["id"], end, edge[end]))
        self._check_spacing(path, data["nodes"])
        for edge in data["edges"]:
            if len(edge.get("label", "")) > DIAGRAM_MAX_LABEL:
                self.error(path, "edge '%s': nhãn dài quá %d ký tự, sẽ che node trên điện thoại" % (edge["id"], DIAGRAM_MAX_LABEL))
        known = node_ids | edge_ids
        for i, step in enumerate(data["steps"]):
            for ref in step["show"] + step.get("highlight", []):
                if ref not in known:
                    self.error(path, "steps[%d]: không có node/edge '%s'" % (i, ref))

    # ---------- biên dịch ----------

    def build(self, out_dir, version):
        """Biên dịch sang dist/. Gọi validate() trước; có lỗi thì không build."""
        if self.errors:
            raise ContentError("còn lỗi, chạy scripts/validate để xem")
        out = Path(out_dir)
        if out.exists():
            for item in out.iterdir():
                item.unlink()
        out.mkdir(parents=True, exist_ok=True)

        entries = [
            _write(out, "tracks.json", _strip(self.tracks), "tracks"),
            _write(out, "glossary.json", _strip(self.glossary), "glossary"),
            _write(out, "project-questions.json", _strip(self.project_questions), "projectQuestions"),
        ]
        for topic in self.topics:
            compiled, images = self._compile_topic(topic)
            entry = _write(out, "topic-%s.json" % topic.id, compiled, "topic")
            entry["id"] = topic.id
            entry["minAppVersion"] = topic.meta["minAppVersion"]
            entries.append(entry)
            for source, name in images:
                data = source.read_bytes()
                (out / name).write_bytes(data)
                entries.append(_entry(name, "image", data))

        manifest = {
            "schemaVersion": MANIFEST_SCHEMA_VERSION,
            "contentVersion": version,
            "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "files": sorted(entries, key=lambda e: e["name"]),
        }
        problems = self.validator.validate(manifest, "manifest.schema.json")
        if problems:
            raise ContentError("manifest không hợp lệ: %s" % problems)
        (out / "manifest.json").write_text(_dump(manifest), encoding="utf-8")
        return manifest

    def _compile_topic(self, topic):
        folder, meta = topic.folder, topic.meta
        images = {}

        def rewrite(text):
            def replace(match):
                source = folder / match.group(1)
                name = "img-%s-%s" % (topic.id, source.name)
                images[source] = name
                return "](%s)" % name
            return IMAGE_RE.sub(replace, text)

        blocks = []
        for block in meta["blocks"]:
            kind = block["type"]
            if kind == "callout":
                compiled = {"type": kind, "style": block["style"], "markdown": block["markdown"]}
            elif kind == "analogy":
                compiled = {"type": kind, "markdown": _read(folder / block["file"])}
            elif kind == "layered":
                compiled = dict({"type": kind}, **split_layered(_read(folder / block["file"])))
            elif kind == "code":
                compiled = {
                    "type": kind,
                    "language": (folder / block["file"]).suffix.lstrip(".") or "text",
                    "code": _read(folder / block["file"]).rstrip("\n"),
                }
                if "caption" in block:
                    compiled["caption"] = block["caption"]
            else:
                compiled = dict({"type": kind}, **_strip(_load(folder / block["file"])))
            blocks.append(compiled)

        result = {key: value for key, value in _strip(meta).items() if key != "blocks"}
        result["blocks"] = blocks
        cards = folder / "flashcards.json"
        result["flashcards"] = _load(cards)["cards"] if cards.exists() else []
        quiz = folder / "quiz.json"
        result["quiz"] = _load(quiz)["questions"] if quiz.exists() else []
        return _map_strings(result, rewrite), sorted(images.items(), key=lambda item: item[1])


def split_layered(text):
    """Tách layered.md thành quick / interview / deep theo các heading '## Quick', '## Interview', '## Deep'."""
    parts, current, found = {}, None, []
    for line in text.splitlines():
        heading = line.strip()
        if heading.startswith("## ") and heading[3:].strip() in LAYERED_SECTIONS:
            current = heading[3:].strip()
            found.append(current)
            parts[current] = []
        elif current:
            parts[current].append(line)
    if found != LAYERED_SECTIONS:
        raise ContentError("cần đúng 3 heading theo thứ tự: ## Quick, ## Interview, ## Deep")
    result = {}
    for name in LAYERED_SECTIONS:
        body = "\n".join(parts[name]).strip()
        if not body:
            raise ContentError("phần '## %s' đang trống" % name)
        result[name.lower()] = body
    return result


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _map_strings(value, transform):
    if isinstance(value, str):
        return transform(value)
    if isinstance(value, dict):
        return {key: _map_strings(item, transform) for key, item in value.items()}
    if isinstance(value, list):
        return [_map_strings(item, transform) for item in value]
    return value


def _strip(data):
    return {key: value for key, value in data.items() if key != "$schema"}


def _read(path):
    return path.read_text(encoding="utf-8")


def _load(path):
    return json.loads(_read(path))


def _dump(data):
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"


def _entry(name, kind, data):
    return {"name": name, "kind": kind, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}


def _write(out, name, data, kind):
    raw = _dump(data).encode("utf-8")
    (out / name).write_bytes(raw)
    return _entry(name, kind, raw)
