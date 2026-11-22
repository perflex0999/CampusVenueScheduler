from contextlib import closing

from app.config import DATABASE
from app.database import connect, initialize_schema
from app.seed import EQUIPMENT, RESERVATIONS, USERS, VENUES, populate_demo


def main():
    with closing(connect(DATABASE)) as db:
        initialize_schema(db)
        populate_demo(db)
    print(f"演示数据库已初始化：{DATABASE}")
    print(f"{len(USERS)} 个账号，{len(VENUES)} 处场地，{len(EQUIPMENT)} 类物资，{len(RESERVATIONS)} 条预约示例。")


if __name__ == "__main__":
    main()
