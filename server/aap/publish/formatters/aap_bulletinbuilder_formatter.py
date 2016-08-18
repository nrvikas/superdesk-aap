# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.publish.formatters import Formatter
import superdesk
import re
from eve.utils import config
from superdesk.utils import json_serialize_datetime_objectId
from superdesk.errors import FormatterError
from superdesk.metadata.item import ITEM_TYPE, PACKAGE_TYPE
from bs4 import BeautifulSoup
from .field_mappers.locator_mapper import LocatorMapper
from .field_mappers.slugline_mapper import SluglineMapper
from .aap_formatter_common import set_subject
from .unicodetoascii import to_ascii
from copy import deepcopy
import json


class AAPBulletinBuilderFormatter(Formatter):
    """
    Bulletin Builder Formatter
    """

    def format(self, article, subscriber, codes=None):
        """
        Formats the article as require by the subscriber
        :param dict article: article to be formatted
        :param dict subscriber: subscriber receiving the article
        :param list codes: selector codes
        :return: tuple (int, str) of publish sequence of the subscriber, formatted article as string
        """
        try:
            formatted_article = deepcopy(article)
            pub_seq_num = superdesk.get_resource_service('subscribers').generate_sequence_number(subscriber)
            body_html = to_ascii(self.append_body_footer(formatted_article)).strip('\r\n')

            # get the desk name
            desk_name = superdesk.get_resource_service('desks').\
                get_desk_name(formatted_article.get('task', {}).get('desk'))

            # force the content to source 'NZN' if desk is 'NZN'
            if 'new zealand' in desk_name.lower().strip():
                formatted_article['source'] = 'NZN'

            formatted_article['body_text'] = self.get_text_content(body_html)
            formatted_article['abstract'] = self.get_text_content(
                to_ascii(formatted_article.get('abstract', '') or '')).strip()
            formatted_article['headline'] = self.get_text_content(
                to_ascii(formatted_article.get('headline', ''))).strip()
            formatted_article['byline'] = self.get_text_content(
                to_ascii(formatted_article.get('byline', '') or '')).strip()

            # get the first category and derive the locator
            category = next((iter(formatted_article.get('anpa_category', []))), None)
            if category:
                locator = LocatorMapper().map(formatted_article, category.get('qcode').upper())
                if locator:
                    formatted_article['place'] = [{'qcode': locator, 'name': locator}]

                formatted_article['first_category'] = category
                formatted_article['first_subject'] = set_subject(category, formatted_article)
                formatted_article['slugline'] = self.get_text_content(
                    to_ascii(SluglineMapper().map(article=formatted_article,
                                                  category=category.get('qcode').upper(), truncate=True)).strip())

            odbc_item = {
                'id': formatted_article.get(config.ID_FIELD),
                'version': formatted_article.get(config.VERSION),
                ITEM_TYPE: formatted_article.get(ITEM_TYPE),
                PACKAGE_TYPE: formatted_article.get(PACKAGE_TYPE, ''),
                'headline': formatted_article.get('headline', '').replace('\'', '\'\''),
                'slugline': formatted_article.get('slugline', '').replace('\'', '\'\''),
                'data': superdesk.json.dumps(formatted_article,
                                             default=json_serialize_datetime_objectId).replace('\'', '\'\'')
            }

            return [(pub_seq_num, json.dumps(odbc_item, default=json_serialize_datetime_objectId))]
        except Exception as ex:
            raise FormatterError.bulletinBuilderFormatterError(ex, subscriber)

    def can_format(self, format_type, article):
        return format_type == 'AAP BULLETIN BUILDER'

    def get_text_content(self, content):
        content = content.replace('<br>', '<br/>').replace('</br>', '')
        soup = BeautifulSoup(content, 'html.parser')

        for top_level_tag in soup.find_all(recursive=False):
            self.format_text_content(top_level_tag)

        return re.sub(' +', ' ', soup.get_text())

    def remove_tags(self, tag, tag_name):
        for replace_tag in tag.find_all(tag_name):
            # remove the <br> tag
            replace_tag.replace_with(' {}'.format(replace_tag.get_text().replace('\n', ' ')))

    def format_text_content(self, tag):
        for child_tag in tag.find_all():
            if child_tag.name == 'br':
                child_tag.replace_with(' {}'.format(child_tag.get_text()))
            else:
                child_tag.replace_with('{}'.format(child_tag.get_text().replace('\n', ' ')))

        para_text = tag.get_text().strip().replace('\n', ' ').replace('\xa0', ' ')
        para_text = re.sub('[\x00-\x1f]', '', para_text)
        if para_text != '':
            tag.replace_with('{}\r\n\r\n'.format(para_text))
        else:
            tag.replace_with('')
