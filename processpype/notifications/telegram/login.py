"""CLI utility for obtaining Telegram session strings.

Requires: telethon, typer (``pip install processpype[telegram]``)
"""

import sys

import typer
from dotenv import load_dotenv
from telethon.sessions import StringSession
from telethon.sync import TelegramClient

load_dotenv()

app = typer.Typer(add_completion=False)


def login(api_id: int, api_hash: str) -> str:
    print(
        "\nYou are now going to login, and the session string will be sent "
        "securely to your telegram account.\n"
        "You need to copy that for future use.\n\n"
    )
    print(
        "If you now login with your phone no, the session string will be "
        "saved in your Telegram's Saved Messages.\n"
    )
    print(
        "If you login with a bot account, the bot will send the session "
        "string to your username."
    )

    input("\nPress [ENTER] to proceed\n")

    with TelegramClient(StringSession(), api_id, api_hash).start() as client:
        session_string = client.session.save()
        message = f"Your session string is: \n\n`{session_string}`\n\nKeep this secret!"

        me = client.get_me()
        print(f"\n\n{me.username}\n\n")
        if me.bot:
            print(
                f"Bot account detected! Open your telegram app, and send "
                f"/start to {me.username}"
            )
            input("Press [ENTER] after you have sent /start\n\n")
            uname = input(
                "What is your telegram username ?\n"
                "(the username of the user account from which you sent "
                "/start to the bot just now)\n: "
            )
            confirm = input("Please type your username again: ")
            if uname == confirm:
                input(
                    f"Are you sure your username is {uname}? Press ENTER to "
                    "continue. The session string will be sent to you."
                )
                client.send_message(uname, message)
                print(f"The session string has been successfully sent to {uname}")
            else:
                print(
                    "The username you typed second time did not match! "
                    "Quitting.\n\nYou can start again!"
                )
                sys.exit(1)
        else:
            client.send_message("me", message)
            print("Open your saved messages in telegram to see your session string!")

    return str(session_string)


@app.command()  # type: ignore[untyped-decorator]
def main(
    api_id: int = typer.Option(
        ...,
        "--api-id",
        help="API ID obtained from my.telegram.org",
        envvar="TELEGRAM_API_ID",
        prompt="Paste your API ID (input hidden)",
        hide_input=True,
    ),
    api_hash: str = typer.Option(
        ...,
        "--api-hash",
        help="API HASH obtained from my.telegram.org",
        envvar="TELEGRAM_API_HASH",
        prompt="Paste your API HASH (input hidden)",
        hide_input=True,
    ),
) -> None:
    """Login to Telegram with user or bot accounts."""
    login(api_id, api_hash)


if __name__ == "__main__":
    app()
