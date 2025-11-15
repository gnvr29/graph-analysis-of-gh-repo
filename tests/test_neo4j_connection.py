import sys
import os
import socket
import traceback
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from config import settings
from neo4j import GraphDatabase


def masked(s):
    if not s:
        return repr(s)
    return s[:8] + '...' if len(s) > 8 else s


def main():
    uri = settings.NEO4J_URI
    user = settings.NEO4J_USERNAME
    pw = settings.NEO4J_PASSWORD

    print("Loaded NEO4J_URI:", uri)
    print("Loaded NEO4J_USERNAME:", masked(user))
    # do NOT print password

    # parse host from uri
    host = None
    m = re.match(r'^[^:]+://([^:/?]+)', uri or '')
    if m:
        host = m.group(1)

    port = 7687
    if host:
        print(f"Testing TCP connection to {host}:{port} (timeout=5s)")
        try:
            sock = socket.create_connection((host, port), timeout=5)
            sock.close()
            print("TCP connection to host:port succeeded.")
        except Exception as e:
            print("TCP connection failed:")
            traceback.print_exc()
    else:
        print("Could not parse host from URI; skipping TCP test.")

    # Try to create driver and verify connectivity
    try:
        print("Attempting to instantiate GraphDatabase.driver and verify_connectivity()")
        driver = GraphDatabase.driver(uri, auth=(user, pw))
        try:
            driver.verify_connectivity()
            print("Driver verify_connectivity succeeded.")
        finally:
            driver.close()
    except Exception as e:
        print("Driver connection failed with exception:")
        traceback.print_exc()

    # Agora tente usar o wrapper Neo4jService (que implementa fallback +ssc)
    try:
        print('\nTentando usar Neo4jService (com fallback automático para +ssc):')
        from src.services.neo4j_service import Neo4jService
        svc = Neo4jService(uri, user, pw)
        try:
            svc.query('RETURN 1 AS x')
            print('Neo4jService query OK')
        finally:
            svc.close()
    except Exception:
        print('Neo4jService attempt failed:')
        traceback.print_exc()


if __name__ == '__main__':
    main()
