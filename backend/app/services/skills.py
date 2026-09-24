import re

VOCABULARY = [
    "Python",
    "JavaScript",
    "TypeScript",
    "Java",
    "React",
    "Next.js",
    "Node.js",
    "SQL",
    "MySQL",
    "PostgreSQL",
    "Docker",
    "Git",
    "Linux",
    "AWS",
    "FastAPI",
    "Django",
    "HTML",
    "CSS",
    "C++",
    "C#",
    "TensorFlow",
    "PyTorch",
    "pandas",
    "NumPy",
    "Excel",
    "Power BI",
    "MongoDB",
    "Redis",
    "Kubernetes",
    "Figma",
    "PHP",
    "Laravel",
    "REST",
    "Machine Learning",
    "Data Analysis",
]
ALIASES = {
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "nodejs": "Node.js",
    "nextjs": "Next.js",
}
ALIASES.update({x.lower(): x for x in VOCABULARY})


def normalize(values):
    result = {}
    for value in values:
        clean = " ".join(value.split()).strip()
        if clean:
            value = ALIASES.get(clean.lower(), clean)
            result[value.casefold()] = value
    return list(result.values())


def infer(text):
    found = []
    for alias, canonical in ALIASES.items():
        if re.search(r"(?<![\w])" + re.escape(alias) + r"(?![\w])", text, re.I):
            found.append(canonical)
    return normalize(found)


def evidence(skills, required):
    known = {x.casefold() for x in normalize(skills)}
    required = normalize(required)
    return [x for x in required if x.casefold() in known], [x for x in required if x.casefold() not in known]
