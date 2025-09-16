# Practical Sessions

## Week 1: Basics of Automated Scientific Discovery of Mind & Brain

> Build a **fully working closed-loop experiment** with AutoRA: fit a model, run an online task with real participants, and use a theory-guided sampler to select experimental conditions.

### Overview

We’ll implement a task-switching experiment using the [Gilbert & Shallice](https://doi.org/10.1006/cogp.2001.0770) model as the guiding theory. By the end, you’ll have a loop that:
1) proposes experimental conditions from theory
2) collects data from human participants online, and
3) updates / fits the model

### Tutorial Structure

We will build a full project in a GitHub repo

If possible, we will use Colab Tutorials to demonstrate usage.

At the end of the session, I will show how to integrate the code into our AutoRA project.


### Prerequisites

- Python 3.11 (or Colab)
- Basic familiarity with Python
- Basic familiarity with GitHub

### Content

```{toctree}
:maxdepth: 1
:titlesonly:

introduction-to-autora/index
psyneulink/index
sweetpea/index
sweetbean/index
autora
```

## Week 2: 