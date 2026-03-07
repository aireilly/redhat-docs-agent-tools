# AsciiDoc module templates

Use these templates when creating new documentation modules. Each module type requires the appropriate `:_mod-docs-content-type:` attribute.

## Assembly template

```asciidoc
:_mod-docs-content-type: ASSEMBLY
include::_attributes/attributes.adoc[]
:context: assembly-name
[id="assembly-file-name"]
= Assembly title
//Add any required context or attributes

[role="_abstract"]
//Short introductory paragraph that provides an overview of the assembly.

include::modules/concept-module.adoc[leveloffset=+1]

include::modules/procedure-module.adoc[leveloffset=+1]

include::modules/reference-module.adoc[leveloffset=+1]
```

## Concept template

```asciidoc
:_mod-docs-content-type: CONCEPT
[id="REPLACE_ME_WITH_ID_{context}"]
= REPLACE_ME_WITH_TITLE
//In the title of concept modules, include nouns or noun phrases that are used in the body text. This helps readers and search engines find the information quickly. Do not start the title of concept modules with a verb.

[role="_abstract"]
//Write a short introductory paragraph that provides an overview of the module. The text that immediately follows the `[role="_abstract"]` tag is used for search metadata.
```

## Procedure template

```asciidoc
:_mod-docs-content-type: PROCEDURE
[id="REPLACE_ME_WITH_ID_{context}"]
= REPLACE_ME_WITH_TITLE

[role="_abstract"]
//Short introductory paragraph that provides an overview of the module. The text that immediately follows the abstract tag is used for search metadata.

.Prerequisites

* List procedure prerequisites one per bullet

.Procedure
//Start each step with an active verb. Use an unnumbered bullet (*) if the procedure includes only one step.

.Verification
//Provide the user with verification methods for the procedure, such as expected output or commands that confirm success or failure.
```

## Reference template

```asciidoc
:_mod-docs-content-type: REFERENCE
[id="REPLACE_ME_WITH_ID_{context}"]
= REPLACE_ME_WITH_TITLE
//In the title of a reference module, include nouns that are used in the body text. For example, "Keyboard shortcuts for ___" or "Command options for ___." This helps readers and search engines find the information quickly.

[role="_abstract"]
//Short introductory paragraph that provides an overview of the module. The text that immediately follows the abstract tag is used for search metadata.

.Labeled list
Term 1:: Definition
Term 2:: Definition

.TABLE_TITLE
[cols="1,2", options="header"]
|===
|Column 1
|Column 2

|Value 1
|Value 2
|===
```

## Snippet template

```asciidoc
:_mod-docs-content-type: SNIPPET
//Snippets are reusable content fragments that can be included in multiple modules.
//Snippets do not have an id or title - they are included inline within other content.

//Add reusable content here that will be included in other modules.
```
