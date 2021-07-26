# chiatter
A chia collection agent/Prometheus client that gathers various stats from a local chia node and exposes them to a Prometheus server & Grafana.

## What do I need to do to get it running on my PC?

**❄** You will need a **python3.6+** environment. Most Linux distros will come with python3 installed - make sure you pick one which comes with **python 3.6** or above.

**❄** The following python3 packages need to be installed: `prometheus_client, chia-blockchain (& dependencies)`. I leave the details up to you. As long as they're in the PYTHONPATH, chiatter will not complain.

**❄** A full chia node running on the same host. No, it's not possible to run it remotely at this point!

**❄** HTTP port 8080 must be open for business (firewalls included), since the Prometheus server will need to access it in order to scrape and aggregate all the stats.

## A Prometheus sever? Grafana? How the heck am I supposed to get those?

It's up to you, really - the simple way is to use docker. Check out my dev "deployment" script in the `misc` folder. It assumes you will want to run the Prometheus server and Grafana containers on the same machine as chiatter - otherwise some tinkering is required in `prometheus.yml` to point it to the host chiatter (and your full chia node) is actually running on.

## Anything else I need to know?

Boy, am I glad you asked! Yes, some stuff.

**❄** Once you get Grafana running for the first time, you will need to create a Prometheus datasource in order to get those nice stats loaded for the charts and all. Here's a nifty screenshot on how to do that (it's simple really):

**❄** Charts? Dashboards? Where, how, you ask? I've included a sample dashboard of my very own design. Find the hidden import dashboard option in Grafana and used the provided json file (also under `misc`). Think of it as an NPC given side-quest and figure it out!

## Why "chiatter"?

Because the exchange of information is key to all great things. So, you know, radio chatter... while crunching on some chia seeds.

## Nothing works! What do I do?

Exactly what you'd do in other situations when nothing works. Raise an issue on github and I'll reply as soon as I can.

## Disclamer

I can not be held responsible for injuries, headaches or curses uttered during the use of this piece of... software. That being said, I welcome constructive suggestions and contributions. Other than that, feel free to use it however you see fit, adapt it, mix it, print the code and tape it to the exterior of an apartment building if that's your thing (why though? perhaps reconsider?).

