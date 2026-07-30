from backend.database.db_manager import DatabaseManager


def test_database_reference_data_and_session(tmp_path):
    manager = DatabaseManager(str(tmp_path / "db.sqlite"))
    manager.init_tables()
    with manager.get_session() as session:
        from backend.database.models import ClinicalGuideline, Drug
        assert session.query(ClinicalGuideline).count() >= 1
        assert session.query(Drug).count() >= 1
    session = manager.get_session()
    manager.close_session(session)

