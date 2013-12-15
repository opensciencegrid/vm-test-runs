#!/usr/bin/python

import re
import os
import sys
import itertools
import yaml
import taglib
from taglib import Tag, SubTag

cwd = os.getcwd()
CSS_URI = "file://%s/vmu.css" % cwd
homepage = "file://%s/results.html" % cwd
pkg_organized_homepage = "file://%s/packages.html" % cwd

os_flavors = [('CentOS','CentOS'),
              ('Red Hat Enterprise Linux Server','Red Hat'),
              ('Scientific Linux','Sci Linux')]

repos = [('3.1; osg','3.1 Release'),
         ('3.1; osg-testing','3.1 Testing'),
         ('3.1; osg > osg-testing','3.1 Release -> 3.1 Testing'),
         ('3.2; osg','3.2 Release'),
         ('3.2; osg-testing','3.2 Testing'),
         ('3.2; osg > osg-testing','3.2 Release -> 3.2 Testing'),
         ('3.1; osg > 3.2/osg','3.1 Release -> 3.2 Release'),
         ('3.1; osg-testing > 3.2/osg-testing','3.1 Testing -> 3.2 Testing')]

packages = [('osg-tested-internal','Everything'),
            ('condor.x86_64, osg-ce-condor, rsv','Condor'),
            ('osg-gridftp, edg-mkgridmap, rsv','GridFTP'),
            ('osg-se-bestman, rsv','BeStMan'),
            ('osg-voms, rsv','VOMS'),
            ('osg-gums, rsv','GUMS')]

def create_html_and_table():
    html = taglib.Html(page_title='OSG VMU Automated Test Results', css_link=CSS_URI)
    html.body.append_new_tag('h1').append('OSG VMU Automated Test Results')
    table = html.body.append_new_tag('table', class_ = 'padded')

    return html, table

def make_data_grid(runs, organization_scheme='repos'):
    organized_runs = [[None] * 6 for i in range(0,48)]
    for run in runs:
        # Find y value in the grid
        for idx, flavor in enumerate(os_flavors):
            if re.match(flavor[0], run['os_release']):
                column = idx
            
        if re.search('6', run['os_release']):
            column = column + 3

        # Find x value in the grid
        for idx, package in enumerate(packages):
            if package[0] == run['param_packages']:
                package_idx = idx

        for idx, repo in enumerate(repos):
            if repo[0] == run['param_sources']:
                repo_idx = idx

        if organization_scheme == 'packages':
            row = repo_idx + package_idx * len(repos)
        else:
            row = package_idx + repo_idx  * len(packages)

        organized_runs[row][column] = run
    return organized_runs

def populate_table(table, data, organization_scheme='repos'):
    if organization_scheme == 'packages':
        sort_link = homepage
        sort_link_text = 'Sort by Release &#9660;'
        first_column_text = 'Parent Package &#9660;'
        second_column_text = 'OSG Release/Upgrade'
        outer_org = packages
        inner_org = repos
    else:
        sort_link = pkg_organized_homepage
        sort_link_text = 'Sort by Package &#9660;'
        first_column_text = 'OSG Release/Upgrade &#9660;'
        second_column_text = 'Parent Package'
        outer_org = repos
        inner_org = packages

    # Create header
    header = Tag("thead")
    row_1 = header.append_new_tag("tr")
    th = row_1.append_new_tag("th", rowspan="2", id = 'sort')
    th.append_new_tag('span', id = 'hide_text').append(first_column_text)
    th.append_new_tag('a', href=sort_link, id = 'sort_link').\
        append(sort_link_text) # mouseover text/link
    row_1.append_new_tag("th", rowspan="2").append(second_column_text)
    row_1.append_new_tag("th", colspan="3").append("EL5")
    row_1.append_new_tag("th", colspan="3").append("EL6")

    row_2 = header.append_new_tag("tr")
    for os in os_flavors * 2:
        row_2.append_new_tag("th").append(os[1])

    # Populate table rows
    table.append(header)
    tbody = table.append_new_tag('tbody')

    for row_tuple, inner in itertools.izip(enumerate(data), itertools.cycle(inner_org)):
        idx = row_tuple[0]
        row = row_tuple[1]
        rowspan_size = len(inner_org)
        if idx % rowspan_size == 0:
            tbody.append_new_tag('tr').append_new_tag('td', class_ = 'divider')
            trow = tbody.append_new_tag('tr')
            trow.append_new_tag('th', rowspan=rowspan_size).append(outer_org[idx/rowspan_size][1])
        else:
            trow = tbody.append_new_tag('tr')
        trow.append_new_tag('th').append(inner[1])
        for column in row:
            trow.append(get_test_numbers(column))

def get_test_numbers(run):
    if run['run_status'] == 0:
        success = run['tests_ok']
        skip = run['tests_ok_skip']
        fail =  run['tests_failed'] + run['tests_error'] + run['tests_bad_skip']
        if fail == 0:
            return Tag('td', class_ = 'result pass', align='center').append("%s %s %s" % (success, skip, fail))
        else:
            return Tag('td', class_ = 'result fail', align='center').append("%s %s %s" % (success, skip, fail))
    else:
        return Tag('td', class_ = 'result die', align='center').append('DIED')
    
def print_html_to_file(html, filename):
    f = open(filename, 'w')
    f.write(str(html))
    f.close()
    
    
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "usage: %s <analyze-test-run file>" % sys.argv[1]
        sys.exit(1)

    # setup html objects
    html_repo, table_repo = create_html_and_table()
    html_package, table_package = create_html_and_table()
    
    # Map runs to their rows
    filename = sys.argv[1]
    f = open(filename, 'r')
    yaml_data = f.read()
    f.close()
    runs = yaml.load(yaml_data)

    repo_organized_runs = make_data_grid(runs)
    populate_table(table_repo, repo_organized_runs)
    print_html_to_file(html_repo, 'results.html')
    
    pkg_organized_runs = make_data_grid(runs, organization_scheme='packages')
    populate_table(table_package, pkg_organized_runs, organization_scheme='packages')
    print_html_to_file(html_package, 'packages.html')
