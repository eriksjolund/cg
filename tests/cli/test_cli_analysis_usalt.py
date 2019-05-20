from cg.store import Store


def test_usalt(invoke_cli, disk_store: Store):

    # GIVEN an initialized database
    db_uri = disk_store.uri

    # WHEN calling usalt without parameters
    result = invoke_cli(['--database', db_uri, 'analysis', 'usalt'])

    # THEN it should ask for the missing options
    assert result.exit_code == 1
    assert 'provide a case' in result.output
    assert 'Aborted!' in result.output


