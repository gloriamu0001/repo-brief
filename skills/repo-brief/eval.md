# Checks before presenting

`build.py --check-render` covers links, paths, sections and layout. Answer these yourself:

1. Can every number and claim on the page be traced to a repo file or an official page the repo links?
2. Is every demo item real output from the repo or its official pages, quoted word for word?
3. Is the page free of captions about itself (source credits, usage hints, requirement lines, file sizes)?
4. Are the concept links the repo's core concepts only, each defined once at its first linkable mention?
5. Does every repo-map item earn its place: used by the workflow or the install, with a content overview?
6. Does the install prompt only install the tool and confirm it worked, with no example run or add-on?
7. Does the swimlane show the pipeline the code actually runs, in order, with step files pointing at the lines that do each step?

## Reader questions

The reader-test subagent answers these from the brief alone and marks every guess:

1. What problem does it solve, and for whom?
2. What is the one idea that makes it work?
3. What do you get out of it? Describe a real output.
4. What are the main steps when it runs, and who or what does each?
5. What are its core concepts, and what does each mean?
6. How do you install it, and how do you know the install worked?
7. Which file would you open first to understand it, and why?
