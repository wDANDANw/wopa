No, please give me detailed information in the form of booky book documents/textbooks of the project to make sure new comers can get to know what is the project, why the project, how the project, etc. that are for ...
[Resolving What, Why, How, etc.]

These documents should form the longitudes and latitudes to include every corner and piece of information in the project.

Now, please plan carefully about what are all the documents we should have. Give me a list of 

./docs folder structure & names
...

Filename: XXX
Purpose: ...
Expected Outcome after reading: ...
Audience: ...
Tone: ...
Details: ...
Outline: ...

---

Must include at least

1. Comprehenisve, Very detailed version of Project General Information & Designs & Philosophies

> Project Philosophies.md
> Project Charter.md
> Proposed Solution & Architectures.md
> Proposed Requirements.md
> Proposed Test Plan.md
> Proposed Use Cases [UC00X]
...

--- Templates of ... --

--- Templates of ... --

2. Then, with these, we shall write the guideline documents for all collaborators / workers on the codesapce

> Project Structure.md
> ..._guidelines.md (like testing_guidelines, code_update_guidelines, modularization_guidelines, etc.)
...

--- Templates of ... --

--- Templates of ... --
3. After that, you should prepare the tracking documents for collaborators to track & onboard

> Current status
> Backlog + ... + 
> Requirements Tracking ->
> Test Tracking
> Feature Tracking --> Status? Todos? Test assigned/mapping (unit/integration/system)? ..?
...

--- Templates of ... --

--- Templates of ... --

--> These documents should have tables and -[] s so the worker can easily know where the project is, what is the next task to do / ongoing, and ...

> Goal: For each new worker, after they read those documents, they should be able to get to every info they need know about what the project is and how should they fix/add code
...

Note: All communication must be done via API calls. Each module should stand alone and work alone. Each module should have their own dockerfile and a manager/server to call to. Unit tests should be conducted within the module. Integration tests are between modules. System test are conducted finally on the system level (fulfilling the use cases breakdowns)
...