# How to use

This project uses [jupyter-book](https://jupyterbook.org/intro.html) to build the materials for the Automated Scientific Discovery of Mind and Brain Workshop.

## Building the book

To build the book locally, you will need to have Python installed. You can then install the required dependencies using pip (best after creating a virtual environment):

```bash
pip install -r requirements.txt
```

To build the book, navigate to the root directory of the project and run:

```bash
jupyter-book build ASDMB_book
```

This will generate the book in the `ASDMB_book/_build/html` directory. You can then open the `index.html` file in your web browser to view the book.

## Contributing
To contribute to the book, most of the time you will only need to edit files in the `ASDMB_book/content` directory. You can add new chapters and sections, or modify existing ones. The book is written in Markdown and Jupyter Notebooks for the tutorials.

You might also have to modify the `ASDMB_book/_toc.yml` file to update the table of contents.

## Please follow these guidelines when contributing:

- Use a separate branch for you changes and make a pull request when you are done.
- Pushing to the `main` branch will trigger a build of the book using GithubActions. Make sure your changes do not break the build (you can check this by first building locally, but you should also check the build status on your pull request and make sure it passes).

