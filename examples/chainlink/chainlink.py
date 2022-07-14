#!/usr/bin/env python3
import asyncio
import pathlib
from datetime import timedelta

from yapapi import Golem
from yapapi.services import Service
from yapapi.log import enable_default_logger
from yapapi.payload import vm


class ChainlinkService(Service):
    @staticmethod
    async def get_payload():
        manifest = "ewogICJ2ZXJzaW9uIjogIjAuMS4wIiwKICAiY3JlYXRlZEF0IjogIjIwMjEtMTEtMDlUMTk6MTk6" \
            "NDEuMDUzNzUyMjgwWiIsCiAgImV4cGlyZXNBdCI6ICIyMDMxLTExLTA3VDE5OjE5OjQxLjA1Mzc1" \
            "NVoiLAogICJtZXRhZGF0YSI6IHsKICAgICJuYW1lIjogImV4YW1wbGUgbWFuaWZlc3QiLAogICAg" \
            "ImRlc2NyaXB0aW9uIjogImV4YW1wbGUgZGVzY3JpcHRpb24iLAogICAgInZlcnNpb24iOiAiMC4x" \
            "LjAiCiAgfSwKICAicGF5bG9hZCI6IFsKICAgIHsKICAgICAgInBsYXRmb3JtIjogewogICAgICAg" \
            "ICJhcmNoIjogIng4Nl82NCIsCiAgICAgICAgIm9zIjogImxpbnV4IgogICAgICB9LAogICAgICAi" \
            "dXJscyI6IFsKICAgICAgICAiaHR0cDovL3lhY24yLmRldi5nb2xlbS5uZXR3b3JrOjgwMDAvZG9j" \
            "a2VyLWNoYWlubGluay1sYXRlc3QtMTNkNDE5YTIyNy5ndm1pIgogICAgICBdLAogICAgICAiaGFz" \
            "aCI6ICJzaGEzOjU1YWExOTA5ZjAzYjU3ZTI1YTJmMTE3OTJkZWQxMDBjNDMwMjk2MzM1ZWQyY2Nm" \
            "OTU1NGRjZjlkIgogICAgfQogIF0sCiAgImNvbXBNYW5pZmVzdCI6IHsKICAgICJ2ZXJzaW9uIjog" \
            "IjAuMS4wIiwKICAgICJzY3JpcHQiOiB7CiAgICAgICJjb21tYW5kcyI6IFsKICAgICAgICAicnVu" \
            "IC4qIiwKICAgICAgICAidHJhbnNmZXIgLioiCiAgICAgIF0sCiAgICAgICJtYXRjaCI6ICJyZWdl" \
            "eCIKICAgIH0sCiAgICAibmV0IjogewogICAgICAiaW5ldCI6IHsKICAgICAgICAib3V0Ijogewog" \
            "ICAgICAgICAgInByb3RvY29scyI6IFsKICAgICAgICAgICAgImh0dHAiLAogICAgICAgICAgICAi" \
            "aHR0cHMiLAogICAgICAgICAgICAid3MiLAogICAgICAgICAgICAid3NzIgogICAgICAgICAgXQog" \
            "ICAgICAgIH0KICAgICAgfQogICAgfQogIH0KfQo="

        manifest_sig = "NxYK5Yjx61rtwAfMvT/psAnGfZZ9HEhpF2fqdJ8LnHMhMVfba+sQ6kbwQekbxp+7" \
            "+R9eD9cRST5HohSD/aKwjPiLb0cuy354IwyRyCFd4z9JQppY5w9X0HCl57L4NU82" \
            "VkTRK2DK735QY6eCmu6GIdlNVNhrTtxgQLCFT/O3TVaTyRbNcT+JcnHgS8gmnvLB" \
            "oOp/vTayNxskxdfGc055bh/Vm/aE4iRI5tKozA7gh9sdRirKqggygktJPVjDRu6E" \
            "GGMfmDslxDWwJoNnx4NOjIk3t7umLeaL5kqYlVNpO7endh40MSQWUdnhfZ0vcg0B" \
            "dIzqFwewswYwo/zoKMNvew=="

        manifest_sig_algorithm = "sha256"

        manifest_cert = "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUZsVENDQTMyZ0F3SUJBZ0lDRUFBd0RRWUpL" \
            "b1pJaHZjTkFRRUxCUUF3Z1pjeEN6QUpCZ05WQkFZVEFsQk0KTVJZd0ZBWURWUVFJREExTlljT0Z3" \
            "b0p2Y0c5c2MydGhNUll3RkFZRFZRUUtEQTFIYjJ4bGJTQk9aWFIzYjNKcgpNUmd3RmdZRFZRUUxE" \
            "QTlIYjJ4bGJTQkxjbUZydzRQQ3MzY3hEakFNQmdOVkJBTU1CVWR2YkdWdE1TNHdMQVlKCktvWklo" \
            "dmNOQVFrQkZoOXdjbnBsYlhsemJHRjNMbmRoYkhOcmFVQm5iMnhsYlM1dVpYUjNiM0pyTUI0WERU" \
            "SXkKTURjeE5EQTJOVGMxT0ZvWERUSXpNRGN5TkRBMk5UYzFPRm93ZlRFTE1Ba0dBMVVFQmhNQ1VF" \
            "d3hGakFVQmdOVgpCQWdNRFUxaHc0WENnbTl3YjJ4emEyRXhGakFVQmdOVkJBb01EVWR2YkdWdElF" \
            "NWxkSGR2Y21zeEdEQVdCZ05WCkJBTU1EMGR2YkdWdElGSmxjWFZsYzNSdmNqRWtNQ0lHQ1NxR1NJ" \
            "YjNEUUVKQVJZVmNtVnhkV1Z6ZEc5eVFHRmsKWkhKbGMzTXVZMjl0TUlJQklqQU5CZ2txaGtpRzl3" \
            "MEJBUUVGQUFPQ0FROEFNSUlCQ2dLQ0FRRUF3Zm9PQUxwcQpDVnhJMWhpTDQzNUJGbFh3WEdkQWxW" \
            "ZDA5cVFxVHNvbXFRVmw3ODYxOUtkREJKNWZtRzdvODFIKzJncDRmbFFFCjl3elR4VnZwYURubVFT" \
            "bTlMcXRyZzF5UVBRZnNjOEljOWg3ZmgyVWtzSU56ZUxEY2p2M2RYWXhHSmc2enZMd3YKK3EyUU9u" \
            "R2xmdS9ZUStQd3h0Yll1N3ptaUNBYUliT3lSSHZXSG9Ja3Y2Ty8xNEJIaUg5YTRNaXZJaDhmN0Rq" \
            "bwo0US8yUWhSczB1TTVNUXRLQ2U3K2xuOGE5S3RqSHZ2QlBoZkMwaDBrallKUlJpTHBPZUpWOVp1" \
            "OXhyOUhTem50CktGVjMxaE5hNHpYUWxlMmliSG5LZTZlN09PYW9BV1MySHlOdTZjRnJwN1UwRThN" \
            "cFJuZVNrT1gzZTVRYnJzUWwKSjFuOWdqMFYyaXlVaHdJREFRQUJvNElCQWpDQi96QUpCZ05WSFJN" \
            "RUFqQUFNQkVHQ1dDR1NBR0crRUlCQVFRRQpBd0lHUURBekJnbGdoa2dCaHZoQ0FRMEVKaFlrVDNC" \
            "bGJsTlRUQ0JIWlc1bGNtRjBaV1FnVTJWeWRtVnlJRU5sCmNuUnBabWxqWVhSbE1CMEdBMVVkRGdR" \
            "V0JCUzZOTElGTXJQTkFPZjBna3J6QXdreUhTcGwxVEJtQmdOVkhTTUUKWHpCZGdCUXpNZmt4Nm9C" \
            "NFo2RlFPT3ZYK2tsbUJSWlJHYUZCcEQ4d1BURUxNQWtHQTFVRUJoTUNVRXd4RmpBVQpCZ05WQkFn" \
            "TURVMWh3NFhDZ205d2IyeHphMkV4RmpBVUJnTlZCQW9NRFVkdmJHVnRJRTVsZEhkdmNtdUNBaEFB" \
            "Ck1BNEdBMVVkRHdFQi93UUVBd0lGb0RBVEJnTlZIU1VFRERBS0JnZ3JCZ0VGQlFjREFUQU5CZ2tx" \
            "aGtpRzl3MEIKQVFzRkFBT0NBZ0VBczgxdTZUT2V6cU1veW8rejcwWU5aQmF0QWQzUk85ZC9xR25R" \
            "QzNtdWxabDFWekxGcllFRwpnOGxhK0cyaVMyYk1LK1ZPNmVZa1NBRndodWkwQnEzSFhtVmorTlVR" \
            "VHpSaEN1aWRrclhlSEY0bnI4QzBqb1YyCnJ3QldKbG9CM3EwaVNJcmlVbzdUcDFDQUJVdFNEaFZu" \
            "UVNwRVdpNUxGLzNDYlhMUWNZa1RNZVJJZjdwMlVwMWsKZU5QcjdTY2V5dFErNThxeTdTbktZUWNI" \
            "YWplbmhyUVJvK1FaS1k0ZkVJc1kzVWhNYkFsM3JEME5UN2dnYmZFOApWY0hXQVpNcEtldlhiL2kx" \
            "MVE1Q0FsRzdXS0Y4MnRLcXFic09ORTlhZWNhWlBNWC9qSXhhSkZDR1dVUGJ4SjNRCnpjK2VmZmpH" \
            "WndDQmNwcWJJdzlha0UvSGdjKzdFcS9tVjFJUGR5UHhRdXhLN214dkQrM3M2U0JlcGNMckF5ckcK" \
            "TUJIdEkybC9Pc1JlcHpDYi9xd29UaDZ4OW1yMk9RWFUxZTgzQ1g4VzZ1ejRQdkErNjRwTmNJMjFP" \
            "ZkRiNEdCbwpNSXpkTk9XVm9KV09KTnMvOHVXQzNqZHVJNXhEQ1NnMGdTV0RmVlBTZlZ0cS8ydU51" \
            "OXFSeFNLdjFiMUc4Z2dLClRVZmtLTVFYTlNYdmRkT2JwUVkvR0xHeGUzSTRGR2F4NmZtWjluc3pF" \
            "cEhJUzdYVXNBMGtmeEt2enJ0Y2FZVnoKOFVEeExyUDVzYzltQVg0TUN3T2ZnSmJqcUxuL0QvOW9x" \
            "TlVvZ2Z2VURqTndXRUFiZ0tyRTJxb3RsUFFSZDFZNgo1VmJRSGFxeXFOMFRBT2dTdXNtcHFqRUVq" \
            "NGpTYjJjcHRQb2p2ZnZyVmkzTS84SlpybHY3YXpZPQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0t" \
            "Cg=="

        return await vm.manifest(
            manifest=manifest,
            manifest_sig=manifest_sig,
            manifest_sig_algorithm=manifest_sig_algorithm,
            manifest_cert=manifest_cert,
            min_mem_gib=2.,
            min_cpu_threads=1,
            capabilities=["inet", "manifest-support"]
        )

    async def start(self):
        async for script in super().start():
            yield script
        script = self._ctx.new_script(timeout=timedelta(minutes=2))
        script.run("/bin/bash", "-c", "/chainlink/run.sh")
        yield script

    async def run(self):
        scr_dir = pathlib.Path(__file__).resolve().parent
        node_id = self._ctx.provider_id
        script = self._ctx.new_script()
        script.upload_file(str(scr_dir / "job.txt"), "/chainlink/data/job.txt")
        script.run("/bin/bash", "-c", "chainlink admin login --file /chainlink/api")
        address = script.run(
            "/bin/bash", "-c", "chainlink keys eth list | grep ^Address: | grep -o 0x.*"
        )
        jobs_create_output = script.run(
            "/bin/bash", "-c", "chainlink jobs create /chainlink/data/job.txt"
        )
        script.run(
            "/usr/bin/wget",
            "--save-cookies",
            "/chainlink/c.txt",
            "--keep-session-cookies",
            "--post-data",
            '{"email": "dummy@email.invalid", "password": "dummy!!!!!PASS123"}',
            "localhost:6688/sessions",
        )
        yield script
        print(
            f"\033[33;1mAddress for provider '{self.provider_name}'\033[0m:",
            (await address).stdout,
            end="",
        )
        print(
            f"\033[33;1mOutput for chainlink jobs create for '{self.provider_name}'\033[0m:",
            (await jobs_create_output).stdout,
            end="",
        )
        while True:
            await asyncio.sleep(3)
            script = self._ctx.new_script()
            future_result = script.run(
                "/bin/bash", "-c", "sleep 1 ; echo $(timeout 5 chainlink local status 2>&1)"
            )
            script.run(
                "/bin/bash",
                "-c",
                "/usr/bin/wget -v --load-cookies /chainlink/c.txt localhost:6688/health -O - 2>&1 >/chainlink/data/health.txt || true",
            )
            script.download_file(
                "/chainlink/data/health.txt", str(scr_dir / f"health-{node_id}.txt")
            )
            script.run(
                "/bin/bash",
                "-c",
                "/usr/bin/wget --load-cookies /chainlink/c.txt localhost:6688/v2/pipeline/runs -v -S -O /chainlink/data/runs.txt -o /chainlink/data/runs-err.txt || true",
            )
            script.download_file("/chainlink/data/runs.txt", str(scr_dir / f"runs-{node_id}.txt"))
            script.download_file(
                "/chainlink/data/runs-err.txt", str(scr_dir / f"runs-err-{node_id}.txt")
            )
            script.download_file(
                "/chainlink/data/chainlink.log", str(scr_dir / f"chainlink-{node_id}.log")
            )
            yield script
            result = (await future_result).stdout
            print(
                f"\033[32;1mStatus for provider '{self.provider_name}'\033[0m:",
                result.strip() if result else "",
            )


async def main():
    async with Golem(budget=1.0, subnet_tag="devnet-beta") as golem:
        cluster = await golem.run_service(ChainlinkService, num_instances=1)
        while True:
            await asyncio.sleep(3)


if __name__ == "__main__":
    enable_default_logger(log_file="chainlink.log")
    loop = asyncio.get_event_loop()
    task = loop.create_task(main())
    loop.run_until_complete(task)
