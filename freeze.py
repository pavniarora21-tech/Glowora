"""Static site generator for GitHub Pages. Run: python freeze.py"""
import os, shutil, sqlite3
from flask_frozen import Freezer
from app import app, DATABASE

user = input("Your GitHub username: ").strip()
repo = input("Repository name [glowora]: ").strip() or "glowora"

app.config["FREEZER_BASE_URL"] = f"https://{user}.github.io/{repo}/"
app.config["FREEZER_DESTINATION"] = "docs"
app.config["FREEZER_REDIRECT_POLICY"] = "ignore"
app.config["FREEZER_IGNORE_404_NOT_FOUND"] = True

# Build only the public pages (no admin/cart/login/account)
freezer = Freezer(app, with_no_argument_rules=False, log_url_for=False)

@freezer.register_generator
def home():
    yield {}

@freezer.register_generator
def shop():
    yield {}

@freezer.register_generator
def product_detail():
    con = sqlite3.connect(DATABASE)
    for (pid,) in con.execute("SELECT id FROM products"):
        yield {"product_id": pid}
    con.close()

if __name__ == "__main__":
    freezer.freeze()
    # GitHub Pages needs .html extension for clean URLs like /shop
    for root, _, files in os.walk("docs"):
        for f in files:
            if "." not in f:
                p = os.path.join(root, f)
                shutil.move(p, p + ".html")
    open("docs/.nojekyll", "w").close()
    print("\nDone! 'docs' folder ready ->", app.config["FREEZER_BASE_URL"])