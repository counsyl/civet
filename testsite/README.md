Test Project for Civet
======================

This Django project demonstrates Civet in action. It also demonstrates how to
have Civet ignore Bower-installed components.

Before running this, have Bower install the dependencies:

    bower install

If you don't have bower installed, make sure you have node.js installed, then:

    npm install -g bower

You also want to install Sass, Compass, and CoffeeScript:

    gem install sass
    gem install compass
    npm install -g coffee-script
    npm install babel-cli babel-preset-es2015

You may also want to install Civet in development mode. Back in this project's
repository root, run:

    python setup.py develop

Once you have everything, run this to see Civet in action:

    python manage.py runserver

Now, modify any Sass or CoffeeScript file in this project, and observe how
the affected Sass/CoffeeScript files get recompiled, with relevant messages
appearing in runserver's output.
