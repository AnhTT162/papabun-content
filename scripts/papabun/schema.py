"""Bộ kiểm tra JSON Schema rút gọn.

Hỗ trợ đúng các từ khóa mà thư mục schema/ đang dùng: type, required, properties,
additionalProperties (false), items, minItems, minLength, pattern, enum, const,
minimum, maximum và $ref tới file khác (kèm #/$defs/...). Gặp từ khóa lạ sẽ báo lỗi
để không âm thầm bỏ qua ràng buộc.
"""

import json
import re
from pathlib import Path

_IGNORED = {"$schema", "$id", "$defs", "title", "description"}
_SUPPORTED = {
    "type", "required", "properties", "additionalProperties", "items", "minItems",
    "minLength", "pattern", "enum", "const", "minimum", "maximum", "$ref",
}

_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


class SchemaValidator:
    def __init__(self, schema_dir):
        self.schema_dir = Path(schema_dir).resolve()
        self._cache = {}

    def _load(self, path):
        path = path.resolve()
        if path not in self._cache:
            self._cache[path] = json.loads(path.read_text(encoding="utf-8"))
        return self._cache[path]

    def validate(self, instance, schema_name):
        """Trả về danh sách lỗi dạng 'đường/dẫn: mô tả'. Rỗng nghĩa là hợp lệ."""
        path = self.schema_dir / schema_name
        errors = []
        self._check(instance, self._load(path), path, "$", errors)
        return errors

    def _resolve(self, ref, base):
        file_part, _, pointer = ref.partition("#")
        target = (base.parent / file_part) if file_part else base
        node = self._load(target)
        for key in [p for p in pointer.split("/") if p]:
            node = node[key]
        return node, target

    def _check(self, value, schema, base, where, errors):
        unknown = set(schema) - _SUPPORTED - _IGNORED
        if unknown:
            raise ValueError("%s: schema dùng từ khóa chưa hỗ trợ %s" % (base.name, sorted(unknown)))

        if "$ref" in schema:
            target, target_base = self._resolve(schema["$ref"], base)
            self._check(value, target, target_base, where, errors)

        if "type" in schema and not _TYPES[schema["type"]](value):
            errors.append("%s: cần kiểu %s" % (where, schema["type"]))
            return
        if "const" in schema and value != schema["const"]:
            errors.append("%s: phải bằng %r" % (where, schema["const"]))
        if "enum" in schema and value not in schema["enum"]:
            errors.append("%s: %r không thuộc %s" % (where, value, schema["enum"]))

        if isinstance(value, str):
            if len(value.strip()) < schema.get("minLength", 0):
                errors.append("%s: không được để trống" % where)
            if "pattern" in schema and not re.search(schema["pattern"], value):
                errors.append("%s: %r không khớp mẫu %s" % (where, value, schema["pattern"]))

        if _TYPES["number"](value):
            if "minimum" in schema and value < schema["minimum"]:
                errors.append("%s: phải >= %s" % (where, schema["minimum"]))
            if "maximum" in schema and value > schema["maximum"]:
                errors.append("%s: phải <= %s" % (where, schema["maximum"]))

        if isinstance(value, list):
            if len(value) < schema.get("minItems", 0):
                errors.append("%s: cần ít nhất %d phần tử" % (where, schema["minItems"]))
            if "items" in schema:
                for i, item in enumerate(value):
                    self._check(item, schema["items"], base, "%s[%d]" % (where, i), errors)

        if isinstance(value, dict):
            for key in schema.get("required", []):
                if key not in value:
                    errors.append("%s: thiếu trường bắt buộc '%s'" % (where, key))
            props = schema.get("properties", {})
            for key, item in value.items():
                if key in props:
                    self._check(item, props[key], base, "%s.%s" % (where, key), errors)
                elif schema.get("additionalProperties") is False:
                    errors.append("%s: trường không hợp lệ '%s'" % (where, key))
