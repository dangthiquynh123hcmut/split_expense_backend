#!/usr/bin/env bash

print() {
    echo -e "$1"
}

print_msg() {
    # Green bold text
    echo -e "\033[1;32m$1\033[0m"
}

print_err() {
    # Red bold text
    echo -e "\033[1;31m$1\033[0m"
}

print_warn() {
    # Yellow bold text
    echo -e "\033[1;33m$1\033[0m"
}
