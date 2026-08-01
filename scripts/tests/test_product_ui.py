from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class ProductUISourceTests(unittest.TestCase):
    def test_root_layout_is_arabic_rtl(self):
        layout = (ROOT / "frontend/app/layout.tsx").read_text()
        self.assertIn('lang="ar"', layout)
        self.assertIn('dir="rtl"', layout)

    def test_required_product_pages_exist(self):
        pages = (
            "frontend/app/login/page.tsx",
            "frontend/app/(dashboard)/page.tsx",
            "frontend/app/(dashboard)/fixtures/page.tsx",
            "frontend/app/(dashboard)/predictions/page.tsx",
            "frontend/app/(dashboard)/sources/page.tsx",
            "frontend/app/(dashboard)/operations/page.tsx",
            "frontend/app/(dashboard)/admin/users/page.tsx",
            "frontend/app/(dashboard)/audit/page.tsx",
            "frontend/app/(dashboard)/settings/page.tsx",
        )
        for page in pages:
            self.assertTrue((ROOT / page).is_file(), page)

    def test_product_pages_do_not_import_mock_data(self):
        for page in (ROOT / "frontend/app").rglob("page.tsx"):
            source = page.read_text().lower()
            self.assertNotIn("mockdata", source, page)
            self.assertNotIn("mock-data", source, page)

    def test_ui_exposes_real_release_and_identity(self):
        dashboard = (ROOT / "frontend/app/(dashboard)/page.tsx").read_text()
        header = (ROOT / "frontend/components/layout/app-header.tsx").read_text()
        self.assertIn("data.system.revision", dashboard)
        self.assertIn("user?.role", header)


if __name__ == "__main__":
    unittest.main()
