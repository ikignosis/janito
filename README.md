# Janito

```bash
$ janito --help
Usage: janito <command>

Interact with Nine API resources. See https://docs.nineapis.ch for the full API docs.

Run "janito <command> --help" for more information on a command.
```

## Setup

```bash
# If you have go already installed
go install github.com/ninech/janito@latest

# Homebrew
brew install ninech/taps/janito

# Debian/Ubuntu
echo "deb [trusted=yes] https://repo.nine.ch/deb/ /" | sudo tee /etc/apt/sources.list.d/repo.nine.ch.list
sudo apt-get update
sudo apt-get install janito

# Fedora/RHEL
cat <<EOF > /etc/yum.repos.d/repo.nine.ch.repo
[repo.nine.ch]
name=Nine Repo
baseurl=https://repo.nine.ch/yum/
enabled=1
gpgcheck=0
EOF
dnf install janito

# Arch
# Install yay: https://github.com/Jguer/yay#binary
yay --version
yay -S janito-bin
```

For Windows users, janito is also built for arm64 and amd64. You can download the
latest exe file from the [releases](https://github.com/ninech/janito/releases) and
install it.

## Getting started

* login to the API using `janito auth login`
* run `janito --help` to get a list of all available commands
