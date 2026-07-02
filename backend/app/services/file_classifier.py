"""
File Classifier

A pure, deterministic classification engine.
Given a filename, it returns the FileCategory that best describes it.

No external calls. No AI. Just fast pattern matching.
Classification priority:
  1. Test files (checked first, as they often share extensions with backend/frontend)
  2. Dependency manifests
  3. Config/Infrastructure files
  4. Documentation
  5. Frontend files
  6. Backend files
  7. Unknown (fallback)
"""
from app.schemas.extraction import FileCategory


# File extension maps
_BACKEND_EXTENSIONS = {
    ".py", ".java", ".go", ".rb", ".php", ".cs", ".cpp", ".c",
    ".h", ".rs", ".swift", ".kt", ".scala", ".r", ".lua"
}

_FRONTEND_EXTENSIONS = {
    ".jsx", ".tsx", ".vue", ".svelte", ".html", ".htm",
    ".css", ".scss", ".sass", ".less", ".styl"
}

# JavaScript/TypeScript are trickier — we check path/name for test patterns first,
# then fall back to frontend vs backend heuristics.
_JS_TS_EXTENSIONS = {".js", ".ts", ".mjs", ".cjs"}

_CONFIG_EXTENSIONS = {
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".env", ".xml", ".properties", ".lock"
}

_DEPENDENCY_FILENAMES = {
    "requirements.txt", "requirements-dev.txt",
    "package.json", "package-lock.json", "yarn.lock",
    "pipfile", "pipfile.lock", "pyproject.toml",
    "go.mod", "go.sum", "gemfile", "gemfile.lock",
    "pom.xml", "build.gradle", "cargo.toml", "cargo.lock"
}

_CONFIG_FILENAMES = {
    "dockerfile", "makefile", ".gitignore", ".dockerignore",
    ".editorconfig", ".eslintrc", ".prettierrc", ".babelrc",
    "nginx.conf", "procfile"
}

_DOC_EXTENSIONS = {".md", ".rst", ".txt", ".adoc", ".tex"}


def _is_test_file(filename: str, stem: str, ext: str) -> bool:
    """Checks if the file is a test file based on common naming conventions."""
    stem_lower = stem.lower()
    filename_lower = filename.lower()
    return (
        stem_lower.startswith("test_")      # Python: test_user.py
        or stem_lower.endswith("_test")     # Go:     user_test.go
        or stem_lower.endswith(".test")     # JS/TS:  user.test.ts
        or stem_lower.endswith(".spec")     # JS/TS:  user.spec.ts
        or "/tests/" in filename_lower      # Directory: /tests/user.py
        or "/test/" in filename_lower       # Directory: /test/user.py
        or "/__tests__/" in filename_lower  # JS convention: /__tests__/user.js
        or "/spec/" in filename_lower       # Ruby convention: /spec/user_spec.rb
    )


def classify_file(filename: str) -> FileCategory:
    """
    Classify a single file by its name into a FileCategory.

    Args:
        filename: The full relative path of the file (e.g., "app/services/user.py").

    Returns:
        A FileCategory enum value.
    """
    import os
    basename = os.path.basename(filename)
    stem, ext = os.path.splitext(basename)
    ext = ext.lower()
    basename_lower = basename.lower()

    # 1. Check for test files first (highest priority)
    if _is_test_file(filename, stem, ext):
        return FileCategory.TEST

    # 2. Dependency manifests
    if basename_lower in _DEPENDENCY_FILENAMES:
        return FileCategory.DEPENDENCY

    # 3. Config/Infrastructure files
    if basename_lower in _CONFIG_FILENAMES or ext in _CONFIG_EXTENSIONS:
        return FileCategory.CONFIG

    # 4. Documentation
    if ext in _DOC_EXTENSIONS:
        return FileCategory.DOCUMENTATION

    # 5. Frontend
    if ext in _FRONTEND_EXTENSIONS:
        return FileCategory.FRONTEND

    # 6. JS/TS — frontend unless it's in a server-style path
    if ext in _JS_TS_EXTENSIONS:
        path_lower = filename.lower()
        if any(seg in path_lower for seg in ["/server/", "/api/", "/backend/", "/routes/", "/controllers/", "/middleware/"]):
            return FileCategory.BACKEND
        return FileCategory.FRONTEND

    # 7. Backend
    if ext in _BACKEND_EXTENSIONS:
        return FileCategory.BACKEND

    # 8. Fallback
    return FileCategory.UNKNOWN
