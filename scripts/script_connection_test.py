import asyncio

from mat.ble.bleak.cc26x2r import BleCC26X2


mac = "60:77:71:22:CA:57"


async def main():

    lc = BleCC26X2()
    n = 1000
    ok = 0

    for i in range(n):
        print("\n\n\ntest {} of {}".format(i, n))
        rv = await lc.connect(mac)
        if rv == 0:
            print("\tconnected to {}".format(mac))
            ok += 1
        else:
            print("\tcould NOT connect")
        await lc.disconnect()
        await asyncio.sleep(2)

        r = int((ok / (i + 1)) * 100)
        print("current OK rate = {}%".format(r))


if __name__ == "__main__":
    asyncio.run(main())
