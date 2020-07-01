#!/usr/bin/env python3
import yaml
import rfeed
from datetime import datetime
import orgparse

def parse_link(line):
    """ return the url and description of the first org link in the string """
    url = line[line.find('[[')+2:line.find('][')]
    text = line[line.find('][')+2:line.find(']]')]
    return {'url': url, 'text': text}


def html_link(url, text):
    """ return a html anchor tag with the given url and description """
    return '<a href="' + url + '">' + text + '</a>'


conf = {}
with open('feed-config.yaml') as f:
    conf = yaml.load(f)

item_conf = conf['item']
org = orgparse.load(conf['org-file'])

items = []
for child in org.children:
    prefix_end = child.heading.find(': ')
    title = child.heading[prefix_end+2:] if prefix_end == -1 else child.heading
    body = iter(child.get_body(format='raw').splitlines())
    pubdate = datetime.strptime(next(body), item_conf['date-format'])
    file_url = parse_link(next(body))['url']
    ep_index = child.properties['INDEX']
    guid_str = ('e' + str(ep_index).rjust(item_conf['episode-digits'], '0')
                + '-' + datetime.strftime(pubdate, '%d%m%Y'))
    desc_dict = {sub.heading: sub.get_body(format='raw')
                 for sub in child.children}
    links = [parse_link(line) for line in desc_dict['Links'].splitlines()]
    itunes_links = '\n'.join(
        [link['text'] + ' - ' + link['url'] for link in links])
    isummary = desc_dict['Notes'] + '\nLinks:\n' + itunes_links
    isubtitle = isummary.splitlines()[0][:255]
    html_links = ['<li>' + html_link(**link) + '</li>' for link in links]
    description = (desc_dict['Notes'] + '\nLinks:\n' + '<![CDATA[<ul>'
                   + ''.join(html_links) + '</ul>]]>')

    itunes_item = rfeed.iTunesItem(
        # TODO check if item property exists before using conf data
        author = conf['itunes:author'],
        image = conf['itunes:image'],
        duration = child.properties['DURATION'],
        explicit = conf['itunes:explicit'],
        episode = ep_index,
        episodeType = item_conf['itunes:episodeType'],
        subtitle = isubtitle,
        summary = isummary)

    item = rfeed.Item(
        title = title,
        description = description,
        guid = rfeed.Guid(guid_str, isPermaLink=False),
        pubDate = pubdate,
        enclosure = rfeed.Enclosure(
            url = file_url,
            length = child.properties['BYTELENGTH'],
            type = item_conf['type']),
        extensions = [itunes_item]
        )

    items.append(item)

itunes = rfeed.iTunes(
    author = conf['itunes:author'],
    subtitle = conf['itunes:subtitle'],
    summary = conf['itunes:summary'],
    image = conf['itunes:image'],
    explicit = conf['itunes:explicit'],
    # TODO extend iTunes class to accept list of categories
    categories = rfeed.iTunesCategory(conf['itunes:categories'][0]),
    owner = rfeed.iTunesOwner(**conf['itunes:owner'])
    )

feed = rfeed.Feed(
    title = conf['title'],
    link = conf['link'],
    description = conf['description'],
    language = conf['language'],
    lastBuildDate = datetime.now(),
    items = items,
    extensions = [itunes]
    )

with open(conf['feed-path'], 'w') as f:
    f.write(feed.rss())

print(f"rss feed written to {conf['feed-path']}")
