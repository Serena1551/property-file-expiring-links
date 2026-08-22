from property_downloads import DownloadRequest, FilePurpose, choose_expiry


def test_tenant_document_gets_the_shortest_download_window() -> None:
    request = DownloadRequest(
        property_id="elm-court-12",
        file_key="properties/elm-court-12/leases/renewal.pdf",
        purpose=FilePurpose.TENANT_DOCUMENT,
    )

    assert choose_expiry(request) == 300
