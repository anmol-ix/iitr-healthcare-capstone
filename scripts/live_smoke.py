"""Real loopback Uvicorn HTTP/WebSocket deployment test, no external network."""
import asyncio
import json
from pathlib import Path
import socket
from threading import Thread
from time import monotonic,sleep
from practo.offline import offline_guard


def main():
    with offline_guard() as attempts:
        import httpx
        import uvicorn
        from websockets.asyncio.client import connect
        from practo.api import create_app
        from practo.service import ClinicService
        service = ClinicService(log_path='.runtime/live-smoke.jsonl')
        sock = socket.socket()
        sock.bind(('127.0.0.1',0))
        port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(create_app(service),host='127.0.0.1',port=port,log_level='error'))
        thread = Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True)
        thread.start()
        deadline = monotonic()+30
        try:
            while not server.started and monotonic()<deadline:
                sleep(.05)
            assert server.started, 'Uvicorn failed to start'
            url = f'http://127.0.0.1:{port}'
            with httpx.Client(trust_env=False) as client:
                health = client.get(url+'/health')
                assert health.status_code == 200
                answer = client.post(url+'/ask',json={'query':'Check APT-010','session_id':'live-http'})
                assert answer.status_code == 200
                assert answer.json()['response_format']['lookup']['record_id'] == 'APT-010'
                async def dialogue():
                    async with connect(f'ws://127.0.0.1:{port}/chat',proxy=None) as ws:
                        results = []
                        for q in ['Status of APT-011','What is its fee?']:
                            await ws.send(json.dumps({'query':q,'session_id':'live-ws'}))
                            result = json.loads(await ws.recv())
                            assert result['response_format']['lookup']['record_id'] == 'APT-011'
                            results.append(result)
                        return results
                websocket = asyncio.run(dialogue())
                after = client.get(url+'/health')
                assert after.status_code == 200
                report = {'server':'Uvicorn on real loopback TCP socket','health_status':health.status_code,
                          'http_result':answer.json(),'websocket_turns':websocket,
                          'health_after_websocket_disconnect':after.status_code,'external_network_attempts':attempts}
                Path('evidence/live_deployment.json').write_text(json.dumps(report,indent=2)+'\n')
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            sock.close()
        assert not thread.is_alive()
        assert attempts == []
        print('Live HTTP and WebSocket smoke test passed; server survived disconnect.')


if __name__ == '__main__':
    main()
