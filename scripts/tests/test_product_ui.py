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

    def test_mobile_navigation_is_accessible_and_closable(self):
        header = (ROOT / "frontend/components/layout/app-header.tsx").read_text()
        sidebar = (ROOT / "frontend/components/layout/app-sidebar.tsx").read_text()
        for marker in ('aria-expanded={menuOpen}', 'aria-controls="mobile-navigation"'):
            self.assertIn(marker, header)
        for marker in ('event.key === "Escape"', 'document.body.style.overflow = "hidden"',
                       'onClick={onClose}', 'id="mobile-navigation"'):
            self.assertIn(marker, sidebar)

    def test_source_admin_ui_never_reads_a_saved_secret(self):
        page = (ROOT / "frontend/app/(dashboard)/sources/page.tsx").read_text()
        service = (ROOT / "frontend/services/operations.ts").read_text()
        self.assertIn('type="password"', page)
        self.assertIn("secret_configured", page)
        self.assertNotIn("s.secret}", page)
        for operation in ("createSource", "replaceSource", "testSource"):
            self.assertIn(operation, service)

    def test_prediction_time_is_rendered_in_baghdad(self):
        card = (ROOT / "frontend/components/predictions/prediction-card.tsx").read_text()
        page = (ROOT / "frontend/app/(dashboard)/predictions/page.tsx").read_text()
        self.assertIn('timeZone: "Asia/Baghdad"', card)
        self.assertIn("sortUpcomingPredictions", page)
        self.assertIn("leftTime-rightTime", page)
        self.assertIn("fixture_id.localeCompare", page)


if __name__ == "__main__":
    unittest.main()
