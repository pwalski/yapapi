import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
import logging
import pathlib
import random
import string
import sys
from typing import List

from yapapi import (
    Golem,
    Task,
    WorkContext,
)
from yapapi.payload.package import Package
from yapapi.props import (
    base as prop_base,
    inf,
)
from yapapi.props.builder import DemandBuilder

examples_dir = pathlib.Path(__file__).resolve().parent.parent
sys.path.append(str(examples_dir))

from utils import (
    build_parser,
    TEXT_COLOR_CYAN,
    TEXT_COLOR_DEFAULT,
    TEXT_COLOR_YELLOW,
    TEXT_COLOR_MAGENTA,
    run_golem_example,
    print_env_info,
)

logger = logging.getLogger(__name__)


@dataclass
class RuntimeConstraints:
    pass


@dataclass
class RuntimePackage(Package):
    constraints: RuntimeConstraints

    async def resolve_url(self) -> str:
        return ""

    async def decorate_demand(self, demand: DemandBuilder):
        demand.ensure(str(self.constraints))


def create_constraints(service_name: str) -> RuntimeConstraints:
    @dataclass
    class Constraints(RuntimeConstraints):
        capabilities: List[str] = prop_base.constraint(
            "golem.runtime.capabilities", operator="=", default_factory=list
        )
        runtime: str = prop_base.constraint(
            inf.INF_RUNTIME_NAME, operator="=", default=service_name
        )

        def __str__(self):
            return prop_base.join_str_constraints(prop_base.constraint_model_serialize(self))

    return Constraints()


def generate_password(length: int) -> str:
    return "".join([random.choice(string.ascii_letters + string.digits) for _ in range(length)])


async def main(
    service_name: str,
    num_users: int,
    max_workers: int,
    running_time: int,
    subnet_tag,
    payment_driver=None,
    payment_network=None,
):
    payload = RuntimePackage(create_constraints(service_name))

    async def worker(ctx: WorkContext, tasks):
        async for task in tasks:
            print(
                f"{TEXT_COLOR_CYAN}"
                f"Running on {ctx.provider_id} (aka {ctx.provider_name})"
                f"{TEXT_COLOR_DEFAULT}",
            )

            # generate a list of user credentials
            users = [(f"user{i}", generate_password(16)) for i in range(1, 1 + num_users)]

            script = ctx.new_script()

            user_futures = [
                script.run("user", "add", username, password) for username, password in users
            ]
            service_future = script.run("service", "info")

            yield script

            for future in user_futures:
                await future
            info_str = await service_future

            print(
                f"{TEXT_COLOR_CYAN}" f"Service information:" f"{TEXT_COLOR_DEFAULT}",
            )

            info = json.loads(info_str.stdout)
            print(json.dumps(info, indent=4, sort_keys=True))

            print(
                f"{TEXT_COLOR_CYAN}" f"Registered credentials:" f"{TEXT_COLOR_DEFAULT}",
            )

            https_templ = string.Template(
                "wget -d --no-check-certificate --http-user $username --http-password $password "
                "$proto://$addr:$port/index.html -O-"
            )
            http_templ = string.Template(
                "$proto://$username:$password@$addr:$port"
            )
            http2_templ = string.Template(
                "$proto://$username:$password@$addr:$port/subdir"
            )

            for username, password in users:
                print(
                    f"{TEXT_COLOR_MAGENTA}" f"{username} {password}" f"{TEXT_COLOR_DEFAULT}",
                )

                if "portHttp" in info and info["portHttp"]:
                    print(
                        http_templ.substitute(
                            username=username,
                            password=password,
                            addr=info["serverName"][0],
                            proto="http",
                            port=info["portHttp"][0],
                        )
                    )
                    print(
                        http2_templ.substitute(
                            username=username,
                            password=password,
                            addr=info["serverName"][0],
                            proto="http",
                            port=info["portHttp"][0],
                        )
                    )

                if "portHttps" in info and info["portHttps"]:
                    print(
                        https_templ.substitute(
                            username=username,
                            password=password,
                            addr=info["serverName"][0],
                            proto="https",
                            port=info["portHttps"][0],
                        )
                    )

            await asyncio.sleep(running_time)
            task.accept_result(result="ready")
            await tasks.aclose()

    if num_users < 1:
        raise RuntimeError(f"Number of users is too small: {num_users}")
    if running_time < 1:
        raise RuntimeError(f"Running time is too short: {num_users}")

    async with Golem(
        budget=1,
        subnet_tag=subnet_tag,
        payment_driver=payment_driver,
        payment_network=payment_network,
    ) as golem:
        print_env_info(golem)

        tasks: List[Task] = [Task(i) for i in range(max_workers)]

        async for task in golem.execute_tasks(worker, tasks, payload, max_workers=max_workers):
            print(f"{TEXT_COLOR_MAGENTA}{task.result}{TEXT_COLOR_DEFAULT}")


if __name__ == "__main__":
    parser = build_parser("Example HTTP auth service")
    parser.add_argument(
        "--service",
        type=str,
        default="golem-factory-http-auth-example",
        help="Service name",
    )
    parser.add_argument(
        "--users",
        type=int,
        default=4,
        help="Number of scans at the same time",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=1,
        help="Number of scans at the same time",
    )
    parser.add_argument(
        "--running-time",
        default=3600,
        type=int,
        help=(
            "How long should the instance run before the cluster is stopped "
            "(in seconds, default: %(default)s)"
        ),
    )

    now = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
    parser.set_defaults(log_file=f"http-auth-yapapi-{now}.log")
    args = parser.parse_args()

    run_golem_example(
        main(
            service_name=args.service,
            num_users=args.users,
            max_workers=args.max_workers,
            running_time=args.running_time,
            subnet_tag=args.subnet_tag,
            payment_driver=args.payment_driver,
            payment_network=args.payment_network,
        ),
        log_file=args.log_file,
    )
