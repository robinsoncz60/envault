# envault

> A CLI tool to encrypt, version, and sync `.env` files across teams using age encryption and S3-compatible backends.

---

## Installation

```bash
pip install envault
```

Or with [pipx](https://pypa.github.io/pipx/) (recommended):

```bash
pipx install envault
```

---

## Usage

**Initialize a new vault in your project:**

```bash
envault init --bucket s3://my-team-bucket --region us-east-1
```

**Push your local `.env` to the vault:**

```bash
envault push --env .env --key age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p
```

**Pull the latest version to your local machine:**

```bash
envault pull --out .env
```

**List available versions:**

```bash
envault versions
```

**Rotate encryption keys:**

```bash
envault rekey --new-key age1newkeyhere...
```

---

## How It Works

1. Encrypts your `.env` file locally using [age](https://github.com/FiloSottile/age) encryption before it ever leaves your machine.
2. Uploads the encrypted blob to your S3-compatible backend (AWS S3, MinIO, Backblaze B2, etc.).
3. Tracks versions automatically so your team can roll back to any previous state.

---

## Requirements

- Python 3.9+
- An S3-compatible storage bucket
- An `age` key pair (`age-keygen` to generate one)

---

## License

[MIT](LICENSE)