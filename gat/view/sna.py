from flask import Blueprint, render_template
import warnings

sna = Blueprint('sna', __name__)


@sna.route('/sheet/<int:case_num>', methods = ['GET', 'POST'])
def sheetSelect(case_num):
    fileDict = caseDict[case_num]
    inputFile = fileDict['SNA_Input']
    workbook = xlrd.open_workbook(inputFile, on_demand = True)
    fileDict['sheets'] = workbook.sheet_names()

    # if workbook only has one sheet, the user shouldn't have to specify it
    if len(fileDict['sheets']) == 1:
        fileDict['nodeSheet'] = fileDict['sheets'][0]
        fileDict['attrSheet'] = None
        return redirect(url_for('nodeSelect', case_num = case_num))

    if request.method == 'POST':
        fileDict['nodeSheet'] = request.form.get('nodeSheet')
        fileDict['attrSheet'] = request.form.get('attrSheet')
        return redirect(url_for('nodeSelect', case_num = case_num))

    return render_template("sheetselect.html",
        sheets = fileDict['sheets'], case_num = case_num)

@sna.route('/nodeinfo/<int:case_num>', methods = ['GET', 'POST'])
def nodeSelect(case_num):

    fileDict = caseDict[case_num]
    graph = SNA.SNA(fileDict['SNA_Input'], nodeSheet = fileDict['nodeSheet'], attrSheet = fileDict['attrSheet'])
    fileDict['graph'] = graph

    if request.method == 'POST':

        nodeColNames = []
        # Commented code is for multiple source columns
        # sourceColNames = []
        i = 0
        for header in graph.header:
            fileDict[header + "IsNode"] = True if request.form.get(header + "IsNode")=="on" else False
            # fileDict[header + "IsSource"] = True if request.form.get(header + "IsSource") == "on" else False
            #fileDict[header + "Class"] = request.form[header + "Class"]
            fileDict[header + "Name"] = request.form[header + "Name"]
            if fileDict[header + "IsNode"] == True:
                nodeColNames.append(fileDict[header + "Name"])
            # if fileDict[header + "IsSource"] == True:
            #     sourceColNames.append(fileDict[header + "Name"])
            i+=1
        fileDict['nodeColNames'] = nodeColNames
        # fileDict['sourceColNames'] = sourceColNames
        graph.createNodeList(nodeColNames)
        graph.createEdgeList(nodeColNames[0])
        if fileDict['attrSheet'] != None:
            graph.loadAttributes()
            graph.calculatePropensities(emo=True)
        # Only the first column is a source
        graph.closeness_centrality()
        graph.degree_centrality()
        graph.betweenness_centrality()
        return redirect(url_for('visualize', case_num=case_num))

    return render_template("nodeselect.html",
        nodes = graph.header, case_num = case_num)

@sna.route('/edgeinfo/<int:case_num>', methods = ['GET', 'POST'])
def edgeSelect(case_num):
    # deprecated by Ryan Steed 20 Jul 2017, replaced by check box in nodeselect.html
    warnings.warn("deprecated", DeprecationWarning, stacklevel=2)
    fileDict = caseDict[case_num]
    graph = fileDict['graph']
    combos = fileDict['nodeColNames']
    fileDict['combos'] = combos

    if request.method == 'POST':
        for combo in combos:
            if request.form.get(combo) == "on":
                graph.createEdgeList(combo)

        graph.closeness_centrality()
        graph.degree_centrality()
        graph.betweenness_centrality()

        return redirect(url_for('visualize', case_num = case_num))


    return render_template("edgeselect.html",
        combos = combos, case_num = case_num)


@application.route('/snaviz/<int:case_num>', methods = ['GET', 'POST'])
def jgvis(case_num):
    fileDict = caseDict[case_num]
    #jgdata = fileDict.get('jgdata')
    graph = fileDict.get('copy_of_graph')
    jgdata, SNAbpPlot, attr, systemMeasures = SNA2Dand3D(graph, request, case_num, _2D = False)
    if request.method == 'POST':
        jgdata, SNAbpPlot, attr, systemMeasures = SNA2Dand3D(graph, request, case_num, _2D = True)
    return render_template("Jgraph.html",
            jgdata = jgdata,
            SNAbpPlot = SNAbpPlot,
            attr = attr,
            graph = graph,
            colors = colors,
            case_num = case_num,
            systemMeasures = systemMeasures
        )

@application.route("/_get_node_data/<int:case_num>")
def get_node_data(case_num):
    fileDict = caseDict[case_num]
    graph = fileDict.get('copy_of_graph')
    name = request.args.get('name', '', type=str)
    if graph == None or len(graph.G) == 0:
        return jsonify(	name=name,
                        eigenvector=None,
                        betweenness=None
                        )
    graph.closeness_centrality()
    graph.betweenness_centrality()
    graph.degree_centrality()
    # graph.katz_centrality()
    graph.eigenvector_centrality()
    graph.load_centrality()
    if graph.eigenvector_centrality_dict != {} and graph.eigenvector_centrality_dict != None:
        eigenvector = str(round(graph.eigenvector_centrality_dict.get(name),4));
    else:
        eigenvector="clustering not available"
    if graph.betweenness_centrality_dict != {} and graph.betweenness_centrality_dict != None:
        betweenness = str(round(graph.betweenness_centrality_dict.get(name),4));
    else:
        betweenness="clustering not available"
    attributes = graph.get_node_attributes(name)
    toJsonify = dict(name=name,
                     eigenvector=eigenvector,
                     betweenness=betweenness,
                     attributes=attributes)
    return jsonify(toJsonify)

@application.route("/_get_edge_data/<int:case_num>")
def get_edge_data(case_num):
    fileDict = caseDict[case_num]
    graph = fileDict.get('copy_of_graph')
    name = request.args.get('name', '', type=str)
    if graph == None or len(graph.G) == 0:
        return jsonify(name=name)
    pair = name.split(",")
    link = graph.G[pair[0]][pair[1]]
    toJsonify = dict(name=name,source=pair[0],target=pair[1])
    for attr in link:
        toJsonify[attr] = link[attr]
    return jsonify(toJsonify)