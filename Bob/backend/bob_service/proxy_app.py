from zaslon_shared.proxy import create_role_proxy


app = create_role_proxy(role="BOB", browser_origin="http://127.0.0.1:5175")

