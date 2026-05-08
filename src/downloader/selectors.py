"""Centralized selector fallback lists for Moodle navigation."""

CAMPUS_URL = "http://campusvirtual.uno.edu.ar/moodle"
LOGIN_URL = f"{CAMPUS_URL}/login/index.php"

SKIP_PATTERNS = [
    "/forum/", "/quiz/", "/assign/", "/page/", "/url/",
    "/chat/", "/choice/", "/survey/", "/wiki/", "/lesson/",
]

SELECTORS: dict[str, list[str]] = {
    "login_user":   ["input[name=username]", "#username"],
    "login_pass":   ["input[name=password]", "#password"],
    "login_submit": ["#loginbtn", "input[type=submit]", "button[type=submit]"],
    "course_link": [
        "a[href*='/course/view.php']",
        "[data-region='myoverview'] a[href*='course/view.php']",
        ".dashboard-card-link",
        "a.coursename",
        ".course-info-container a[href*='course/view.php']",
        "[data-region='course-content'] a[href*='course/view.php']",
        "h3.coursename a",
        ".coursebox a",
    ],
    "activity_link": [
        ".activityinstance a",
        ".activity a.aalink",
        "[data-activityname] a",
        "li.activity a[href*='/mod/']",
    ],
    "modified_time": [
        "time[datetime]",
        ".resourcelastmodified",
        ".modified",
        ".filedetails dd",
        ".resourceworkaround",
    ],
}


def first_match(page, key: str):
    """Try each selector for key; return first locator with >=1 element, else None."""
    for sel in SELECTORS[key]:
        loc = page.locator(sel)
        try:
            if loc.count() > 0:
                return loc
        except Exception:
            continue
    return None
