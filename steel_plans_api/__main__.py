import uvicorn


def main():
    uvicorn.run("steel_plans_api.endpoints:app")


if __name__ == '__main__':
    main()
