---                                                                             
layout: default                                                                 
title: Development Guide
nav_order: 3
---                                                                             

# Development Guide                                                                    
{: .no_toc }                                                                    

## Table of contents                                                            
{: .no_toc .text-delta }                                                        

1. TOC                                                                          
{:toc}    


The plugin team welcomes your contributions to the project. 
Please use this document as a guide to working on proposed changes to Linchpin Plugin. 
We ask that you read through this document to ensure you understand our development model and 
best practices before submitting changes.

## Branch Model
We follow a git-flow type of model. Currently there are two branches
* Develop - where all current work is done
* Master - stable release

Both branches are protected in our gitlab. We do not allow commits directly to either branch. Only the maintainers
are allowed to cut a release and request a merge of `develop` into `master`. 
All contributors should create new work branches off the `develop` and request a merge to `develop` when ready. 

## How to setup your development environment
Lets first clone the source code
```bash
git clone https://gitlab.cee.redhat.com/ccit/teflo/plugins/teflo_linchpin_plugin.git

```

Next lets create a Python virtual environment for teflo. This assumes you have virtualenv package installed.
```bash
$ mkdir ~/.virtualenvs
$ virtualenv ~/.virtualenvs/lp_plugin
$ source ~/.virtualenvs/lp_plugin/bin/activate
```

Now that we have our virtual environment created. Lets go ahead and install the Python packages used for development.
```bash
(lp_plugin) $ pip install -r teflo_linchpin_plugin/test-requirements.txt
```

Let’s create our new branch from develop
```bash
(lp_plugin) $ git checkout develop
(lp_plugin) $ git checkout -b <new branch>
```

Finally install the plugin itself using editable mode. This will install teflo for you. 
```bash
(lp_plugin) $ pip install -e teflo_linchpin_plugin/.
```

You can verify teflo is installed by running the following commands.
```bash
(lp_plugin) $ teflo
(lp_plugin) $ teflo --version
```

## How to run tests locally
You can run the unit tests and verify pep8 by the following command:
```bash
(lp_plugin) $ make test-functional
```

This make target is actually executing the following tox environments:
```bash
(lp_plugin) $ tox -e py27-unit
(lp_plugin) $ tox -e py3-unit
```
We have the following standards and guidelines

* All tests must pass
* Code coverage must be above 50%
* Code meets PEP8 standards
* There should be tests included with the code changes where possible
* There should be documentation included with the code changes where possible

Before any change is proposed to the plugin we ask that you run the tests to verify the above standards. 
If you forget to run the tests, we have a 
[Jenkins](https://ci-ops-jenkins.rhev-ci-vms.eng.rdu2.redhat.com/view/teflo/job/cbn-linchpin-provisioner-tier-0/)
job that runs through these on any changes. This allows us to make sure each patch meets the standards.

If there is a reason that the changes don’t have any accompanying tests we should 
be annotating the code changes with TODO comments with the following information:

* State that the code needs tests coverage
* Quick statement of why it couldn’t be added.

## How to submit a change for review
At this point you have your local development environment setup. 
You made some code changes, ran through the unit tests and pep8 validation. 
Before you submit your changes you should check a few things:

If the develop branch has changed since you last pulled it down it is 
important that you get the latest changes in your branch. You can do that in two ways:

Rebase using the local develop branch
```bash
(lp_plugin) $ git checkout develop
(lp_plugin) $ git pull origin develop
(lp_plugin) $ git checkout <branch>
(lp_plugin) $ git rebase develop

```

or 

Rebase using the remote develop branch
```bash
(lp_plugin) $ git pull --rebase origin/develop
```

If you have multiple commits its best to squash them into a single commit. 
The interactive rebase menu will appear and guide you with what you need to do.
```bash
(lp_plugin) $ git rebase -i HEAD~<the number of commits to latest develop commit>
```

You can push then branch upstream
```bash
(lp_plugin) $ git push -u -f  origin <branch>
```

Finally, to submit the MR you can do it a couple ways:

* Use the GitLab `new merge request` wizard. Be sure to select the `develop` branch.
* Install the [lab](https://github.com/zaquestion/lab) command line tool. Using this
tool you can create the GitLab MR straight from your terminal using `lab mr create`

The Jenkins Job will trigger and run tests. Whether the tests pass or fail the job
will post a comment with a status a url to the build. 

If the job fails, there a couple options to retrigger the jobs:
* If it fails for any non-code related issue you can type `test` into
the comment on the MR.

* If it is a code related issue, when you push the changes to your branch
this will re-trigger.

## For Maintainers
Below are some instructions for maintainers. 

Right now the release process is manual. We have a TODO to automate the release process

### Get ready to release 

When you are ready to cut a new release. The process is the following

* First, bump the version of the release appropriately. We follow Semantic 2.0 versioning
```bash
(lp_plugin) $ make bump-[major|minor|patch]
```

* Next, update the `CHANGELOG` file with the required information. The file is in markdown format. 
Below is a helpful template.

```bash
#Version 1.0.0 (2020-04-08)

##New features
* Feature 1

##Enhancements
* Enhancement 1

## Bug Fixes
* Bugg fix 2

## Doc Changes
* Doc Change 1

## Test/CI Enhancements
* Test Added 1
```

* The `bump` command creates a git log entry. Let's add the CHANGELOG update to that git commit
entry.

```bash
(lp_plugin) $ git add CHANGELOG
(lp_plugin) $ git commit --amend --no-edit
```

* At this point you can request an MR to `master` using one of the methods mentioned above. 

* Once the Merge has been approved and commited. You can now create a tagged release in GitLab
Start the `new tag` wizard.
    * `Tag name`: Semantic Version i.e. 1.0.0
    * `Create from`: master
    * `Message`: "Semantic Version" i.e. "1.0.0"
    * `Release notes`: Copy and paste the contents of the `CHANGELOG`
