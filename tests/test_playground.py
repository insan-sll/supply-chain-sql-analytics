import duckdb
import pytest

from scsql.playground import MAX_ROWS, QueryRejected, prepare


@pytest.mark.parametrize(
    "sql",
    ["SELECT 1", "with x as (select 1) select * from x", "-- note\nSELECT 2;", "/* c */ select 3"],
)
def test_accepts_single_select(sql):
    assert prepare(sql).endswith(f"LIMIT {MAX_ROWS}")


@pytest.mark.parametrize(
    "sql",
    ["", "DROP TABLE orders", "SELECT 1; DROP TABLE orders", "COPY orders TO 'x.csv'", "ATTACH 'x.db'"],
)
def test_rejects_everything_else(sql):
    with pytest.raises(QueryRejected):
        prepare(sql)


def test_read_only_connection_blocks_writes(tmp_path, con):
    path = tmp_path / "ro.duckdb"
    con.execute(f"ATTACH '{path}' AS ro")
    con.execute("CREATE TABLE ro.t AS SELECT 1 AS x")
    con.execute("DETACH ro")
    ro = duckdb.connect(str(path), read_only=True, config={"enable_external_access": False})
    with pytest.raises(duckdb.Error):
        ro.execute("DELETE FROM t")
    with pytest.raises(duckdb.Error):
        ro.execute("SELECT * FROM read_csv('/etc/passwd')")
    ro.close()
