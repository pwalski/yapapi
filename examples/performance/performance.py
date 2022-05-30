#!/usr/bin/env python3
import asyncio

from datetime import datetime, timedelta, timezone
from enum import Enum
import pathlib
import sys

from yapapi.script import Script
from yapapi.golem import Golem
from yapapi.payload import vm
from yapapi.services import Service, ServiceState

examples_dir = pathlib.Path(__file__).resolve().parent.parent
sys.path.append(str(examples_dir))

from utils import (
    build_parser,
    TEXT_COLOR_CYAN,
    TEXT_COLOR_DEFAULT,
    run_golem_example,
    print_env_info,
)

# the timeout after we commission our service instances
# before we abort this script
STARTING_TIMEOUT = timedelta(minutes=5)

# additional expiration margin to allow providers to take our offer,
# as providers typically won't take offers that expire sooner than 5 minutes in the future
EXPIRATION_MARGIN = timedelta(minutes=5)

lock = asyncio.Lock()

computation_state_server = {}
computation_state_client = {}
completion_state = {}
ip_provider_id = {}
network_addresses = []


class State(Enum):
    IDLE = 0
    COMPUTING = 1
    FAILURE = 2


class PerformanceScript(Script):
    async def _before(self):
        self.before = datetime.now()
        await super()._before()

    async def _after(self):
        self.after = datetime.now()
        await super()._after()

    def __init__(self, script: Script):
        self.before = None
        self.after = None
        self.timeout = script.timeout
        self.wait_for_results = script.wait_for_results
        self._ctx = script._ctx
        self._commands = script._commands
        self._id: int = script._id

    def calculate_transfer(self, bts):
        dt = self.after - self.before
        return bts / (dt.seconds * 1000 * 1000)


class PerformanceService(Service):
    @staticmethod
    async def get_payload():
        return await vm.repo(
            image_hash="787b3430ee1e431fafa9925b4661414173e892d219db8b53c491636f",
            min_mem_gib=1.0,
            min_storage_gib=0.5,
        )

    async def start(self):
        # perform the initialization of the Service
        # (which includes sending the network details within the `deploy` command)
        async for script in super().start():
            yield script

        script = self._ctx.new_script(timeout=timedelta(minutes=1))
        script.run("/bin/bash", "-c", f"iperf3 -s -D")
        yield script

        server_ip = self.network_node.ip
        ip_provider_id[server_ip] = self.provider_id
        computation_state_server[server_ip] = State.IDLE
        computation_state_client[server_ip] = State.IDLE

        await lock.acquire()
        value = bytes(10000000)
        path = "/golem/output/dummy"
        print(f"Started test transfer between requestor and node: {self.provider_id}")

        script = self._ctx.new_script(timeout=timedelta(minutes=3))
        script.upload_bytes(value, path)
        script = PerformanceScript(script)
        yield script
        speed = script.calculate_transfer(10000000)

        print(f"Transfer speed: {speed} MB/s")

        lock.release()
        print(f"Completed test transfer between requestor and node: {self.provider_id}")

        network_addresses.append(server_ip)

    async def run(self):
        global computation_state_client
        global computation_state_server
        global completion_state

        while len(network_addresses) < len(self.cluster.instances):
            await asyncio.sleep(1)

        client_ip = self.network_node.ip
        neighbour_count = len(network_addresses) - 1
        completion_state[client_ip] = set()

        print(f"{self.provider_id}: running")
        await asyncio.sleep(5)

        while len(completion_state[client_ip]) < neighbour_count:

            for server_ip in network_addresses:
                if server_ip == client_ip:
                    continue
                elif server_ip in completion_state[client_ip]:
                    continue
                elif server_ip not in computation_state_server:
                    continue
                await lock.acquire()
                if computation_state_server[server_ip] != State.IDLE or computation_state_client[server_ip] != State.IDLE or computation_state_server[client_ip] != State.IDLE:
                    lock.release()
                    await asyncio.sleep(1)
                    continue

                computation_state_server[server_ip] = State.COMPUTING
                computation_state_client[client_ip] = State.COMPUTING
                lock.release()

                await asyncio.sleep(1)

                print(f"{self.provider_id}: computing on {ip_provider_id[server_ip]}")

                try:
                    output_file_vpn_transfer = f"vpn_transfer_client_{client_ip}_to_server_{server_ip}_logs.txt"
                    output_file_vpn_ping = f"vpn_ping_node_{client_ip}_to_node_{server_ip}_logs.txt"

                    script = self._ctx.new_script(timeout=timedelta(minutes=3))
                    script.run(
                        "/bin/bash",
                        "-c",
                        f"ping -c 10 {server_ip} > /golem/output/{output_file_vpn_ping}",
                    )
                    yield script

                    script = self._ctx.new_script(timeout=timedelta(minutes=3))
                    dt = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
                    script.download_file(
                        f"/golem/output/{output_file_vpn_ping}", f"golem/output/{dt}_{output_file_vpn_ping}"
                    )
                    yield script

                    script = self._ctx.new_script(timeout=timedelta(minutes=3))

                    script.run(
                        "/bin/bash",
                        "-c",
                        f"iperf3 -c {server_ip} --logfile /golem/output/{output_file_vpn_transfer}",
                    )
                    yield script

                    script = self._ctx.new_script(timeout=timedelta(minutes=3))
                    dt = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
                    script.download_file(
                        f"/golem/output/{output_file_vpn_transfer}", f"golem/output/{dt}_{output_file_vpn_transfer}"
                    )
                    yield script

                    completion_state[client_ip].add(server_ip)
                    print(f"{self.provider_id}: finished on {ip_provider_id[server_ip]}")

                except Exception as error:
                    print(f"Error: {error}")

                await lock.acquire()
                computation_state_server[server_ip] = State.IDLE
                computation_state_client[client_ip] = State.IDLE
                lock.release()

            await asyncio.sleep(1)

        print(f"{self.provider_id}: finished computing")

        # keep running - nodes may want to compute on this node
        while len(completion_state) < neighbour_count or not all(
                [len(c) == neighbour_count for c in completion_state.values()]
        ):
            await asyncio.sleep(1)

        print(f"{self.provider_id}: exiting")

    async def reset(self):
        # We don't have to do anything when the service is restarted
        pass


# Main application code which spawns the Golem service and the local HTTP server
async def main(
        subnet_tag, payment_driver, payment_network, num_instances, running_time, instances=None
):
    async with Golem(
            budget=1.0,
            subnet_tag=subnet_tag,
            payment_driver=payment_driver,
    ) as golem:
        print_env_info(golem)

        commissioning_time = datetime.now()
        global network_addresses

        network = await golem.create_network("192.168.0.1/24")
        cluster = await golem.run_service(
            PerformanceService,
            network=network,
            num_instances=num_instances,
            expiration=datetime.now(timezone.utc)
            + STARTING_TIMEOUT
            + EXPIRATION_MARGIN
            + timedelta(seconds=running_time),
        )

        instances = cluster.instances

        # def still_starting():
        #     return any(i.state in (ServiceState.pending, ServiceState.starting) for i in instances)
        #
        # # wait until all remote http instances are started
        #
        # while still_starting() and datetime.now() < commissioning_time + STARTING_TIMEOUT:
        #     print(f"Cluster is starting. Instances: {instances}")
        #     await asyncio.sleep(5)
        #
        # if still_starting():
        #     raise Exception(
        #         f"Failed to start instances after {STARTING_TIMEOUT.total_seconds()} seconds"
        #     )

        start_time = datetime.now()

        while datetime.now() < start_time + timedelta(seconds=running_time) and len(completion_state) < num_instances - 1 or not all(
                [len(c) == num_instances - 1 for c in completion_state.values()]
        ):
            try:
                await asyncio.sleep(10)
            except (KeyboardInterrupt, asyncio.CancelledError):
                break

        cluster.stop()


if __name__ == "__main__":
    parser = build_parser("NET measurement tool")
    parser.add_argument(
        "--num-instances",
        type=int,
        default=2,
        help="The number of nodes to be tested",
    )
    parser.add_argument(
        "--running-time",
        default=1200,
        type=int,
        help=(
            "How long should the instance run before the cluster is stopped "
            "(in seconds, default: %(default)s)"
        ),
    )
    now = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
    parser.set_defaults(log_file=f"net-measurements-tool-{now}.log")
    args = parser.parse_args()

    run_golem_example(
        main(
            subnet_tag=args.subnet_tag,
            payment_driver=args.payment_driver,
            payment_network=args.payment_network,
            num_instances=args.num_instances,
            running_time=args.running_time,
        ),
        log_file=args.log_file,
    )
