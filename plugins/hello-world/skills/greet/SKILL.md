---
name: greet
description: "Print a greeting message"
argument-hint: "[name]"
---

## Name

hello-world:greet

## Synopsis

`/hello-world:greet [name]`

## Description

Prints a friendly greeting. If a name is provided, the greeting is personalized.

## Implementation

1. If an argument is provided, greet the user by name.
2. Otherwise, print a generic greeting.

Print the greeting to the user:
- With argument: "Hello, {name}!"
- Without argument: "Well hello there!"

## Examples

- `/hello-world:greet` - prints a generic greeting
- `/hello-world:greet Alice` - prints "Hello, Alice! Welcome to Red Hat Docs Agent Tools."
