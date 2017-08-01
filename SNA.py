import networkx as nx
from networkx.algorithms import bipartite as bi
from networkx.algorithms import centrality
# import csv, might deveop in order to read bith xlsx and csv
import xlrd
import matplotlib.pyplot as plt
import tempfile

class SNA():
    def __init__(self, excel_file, nodeSheet, attrSheet = None):
        self.subAttrs = ["W", "SENT", "SZE", "AMT"]
        self.header, self.list = self.readFile(excel_file, nodeSheet)
        if attrSheet != None:
            self.attrHeader, self.attrList = self.readFile( excel_file, attrSheet)
        self.G = nx.complete_multipartite_graph()
        self.nodes = []
        self.edges = []
        self.nodeSet = []
        self.clustering_dict = {}
        self.latapy_clustering_dict = {}
        self.closeness_centrality_dict = {}
        self.betweenness_centrality_dict = {}
        self.degree_centrality_dict = {}
        self.eigenvector_centrality_dict = {}
        self.katz_centraltiy_dict={}
        self.load_centrality_dict = {}
        self.communicability_centrality_dict = {}
        self.communicability_centrality_exp_dict = {}
        self.node_attributes_dict = {}
        self.nodeSet = []
        self.attrSheet = attrSheet

    # Read xlsx file and save the header and all the cells, each a dict with value and header label
    # Input: xlsx file, sheet
    def readFile(self, excel_file, sheet):

        workbook = xlrd.open_workbook(excel_file)
        sh = workbook.sheet_by_name(sheet)
        header = [str(sh.cell(0,col).value).strip("\n") for col in range(sh.ncols)]
        New_ncols = sh.ncols - 1

        # If any, delete all the empty features in the header
        while header[New_ncols] == '':
            header.remove(header[New_ncols])
            New_ncols -= 1

        # a list of nodes
        list = []
        for row in range(1,sh.nrows):
            tempList = []
            for col in range(New_ncols + 1):
                feature = str(sh.cell(0, col).value).strip("\n")
                cell = sh.cell(row,col).value
                if type(cell) == type(""):
                    val = cell.strip("\n")
                else:
                    val = str(cell)
                if val != "": # handle empty cells
                    # Make each node a dict with node name and node header, to assign later
                    tempList.append({'val': val, 'header': feature}) # need to define attributes later
            list.append(tempList)

        # remove repeated column titles
        consolidatedHeader = []
        for feature in header:
            if ( feature not in consolidatedHeader ) and ( feature not in self.subAttrs ) :
                consolidatedHeader.append(feature)

        return consolidatedHeader,list

    #create set of nodes for multipartite graph
    # name = names of the node. This is defined by the header. ex: Abbasi-Davani.F: Name  or Abbasi-Davani.F: Faction leader
    # nodeSet = names that define a set of node. For example, we can define Person, Faction Leader, and Party Leader as "Agent"
    # note: len(name) = len(nodeSet), else code fails
    def createNodeList(self, nodeSet):
        for row in self.list:
            for node in row:
                if node['header'] in nodeSet and node['val'] != "":
                    # strip empty cells
                    self.G.add_node(node['val'], block=node['header'])
        self.nodeSet = nodeSet
        self.nodes = nx.nodes(self.G)

    # Input: header list and list of attributes with header label from attribute sheet
    # Output: updated list of nodes with attributes
    def loadAttributes(self):
        #print("header",self.attrHeader)
        #print("list",self.attrList)
        for row in self.attrList:
            nodeID = row[0]['val']
            for cell in row[1:]:
                if cell['val'] != '':
                    if nodeID in self.nodes:
                        attrList = []
                        node = self.G.node[nodeID]
                        if cell['header'] in self.subAttrs:  # handle subattributes, e.g. weight
                            prevCell = row[row.index(cell) - 1]
                            key = {}
                            while prevCell['header'] in self.subAttrs:
                                key[prevCell['header']] = prevCell['val']
                                prevCell = row[row.index(prevCell) - 1]
                            key[cell['header']] = cell['val']
                            attrList = [ [x,key] for x in node[prevCell['header']] if prevCell['val'] in x ]
                            for x in node[prevCell['header']]:
                                if prevCell['val'] in x:
                                    attrList.append( [x,key] )
                                else:
                                    attrList.append( x )
                            attrID = prevCell['header']
                            # add the attribute as an attr-of-attr
                        else: # if the attribute is not a subattribute
                            if cell['header'] in self.G.node[nodeID]:
                                attrList = (node[cell['header']])
                            attrList.append([cell['val']])
                            attrID = cell['header']
                        self.changeAttribute(nodeID,attrList,attrID)

    def createEdgeList(self, sourceSet):
        list = self.list
        edgeList = []
        for row in list:
            sourceNodes = []
            for node in row:
                if node['header'] in sourceSet:
                    sourceNodes.append(node['val'])
            for source in sourceNodes:
                for node in row:
                    if node['val'] != source and node['header'] in self.nodeSet:
                        edgeList.append( (source,node['val']) ) # create a new link
        self.G.add_edges_from(edgeList)
        self.edges = edgeList
        #print("edges",self.G.edges())

    def addEdges(self, pair): # deprecated, needs fixing - doesn't handle new dict structure
        data = self.list
        #print(self.nodes)
        newEdgeList = []
        for row in data:
            first = row[pair[0]]['val']
            second = row[pair[1]]['val']
            if (first != '' and second != '') and (first != second):
                newEdgeList.append((first, second))
        self.G.add_edges_from(newEdgeList)
        self.edges.extend(newEdgeList)

    def calculatePropensities(self,emo):
        for edge in self.edges: # for every edge, calculate propensities and append as an attribute
            emoPropList = self.emoProp(edge) if emo else None
            self.G[edge[0]][edge[1]]['Emotion'] = emoPropList if len(emoPropList)>1 else None
            if len(emoPropList) > 1:
                print("For edge between",edge[0],"&",edge[1],"emotional propensities:",emoPropList)

    def emoProp(self, edge):
        emoProps = []
        source = self.G.node[edge[0]]
        target = self.G.node[edge[1]]
        for attr in ( target if len(source) > len(target) else source ):
            if attr != 'block' and source.get(attr) is not None and target.get(attr) is not None:
                for src_val in source.get(attr):
                    for trg_val in target.get(attr):
                        if len(src_val) > 1 and len(trg_val) > 1:
                            src_w = float(src_val[1]["W"]) if "W" in src_val[1] else None
                            trg_w = float(trg_val[1]["W"]) if "W" in trg_val[1] else None
                            if src_w is not None and trg_w is not None:
                                # Checking to see if the attribute for each node is equal:
                                if src_val[0] == trg_val[0]:
                                    # Checking to see if each node's attribute weights fall within specified ranges:
                                    if src_w >= 0.8 and trg_w >= 0.8:
                                        emoProps.append("Trust")
                                    elif src_w >= 0.6 and trg_w >= 0.6:
                                        emoProps.append("Joy")
                                    elif src_w >= 0.2 and trg_w >= 0.2:
                                        emoProps.append("Anticipation")
                                    else:
                                        emoProps.append("None")
                                # # Conditional statements for differing emotions - haven't yet defined opposition:
                                # else:
                                #     # Checking to see if each node's attribute weights fall within specified ranges:
                                #     if src_w >= 0.8 and trg_w >= 0.8:
                                #         emoProps.append("Disgust")
                                #     elif src_w >= 0.6 and trg_w >= 0.6:
                                #         emoProps.append("Fear")
                                #     elif src_w >= 0.6 and trg_w >= 0.4:
                                #         emoProps.append("Anger")
                                #     elif src_w >= 0.2 and trg_w >= 0.2:
                                #         emoProps.append("Sadness")
                                #     else:
                                #         emoProps.append("None")
        self.edges = nx.edges(self.G)
        return emoProps

    # copy the origin social network graph created with user input data.
    # this will be later used to reset the modified graph to inital state
    def copyGraph(self):
        self.temp = self.G

    def resetGraph(self):
        self.G = self.temp

    # remove edge and node. Note that when we remove a certain node, edges that are
    # connected to such nodes are also deleted.
    def removeNode(self, node):
        if self.G.has_node(node):
            self.G.remove_node(node)
            self.nodes = nx.nodes(self.G)
        for edge in self.edges:
            if node in edge:
                self.edges.remove(edge)

    def addNode(self,node,attrDict={}, connections=[]):
        self.G.add_node(node,attrDict)
        self.nodes = nx.nodes(self.G)
        for i in connections:
            #print("connecting to:",i)
            self.G.add_edge(node,i)
            self.edges.append([node,i])

    def removeEdge(self, node1, node2):
        if self.G.has_edge(node1,node2):
            self.G.remove_edge(node1,node2)

    # Change an attribute of a node
    def changeAttribute(self, node,  value, attribute="bipartite"):
        if self.G.has_node(node):
            self.G.node[node][attribute] = value
            #print("New attribute for "+node+": "+str(self.G.node[node][attribute]))
        self.nodes = nx.nodes(self.G)

    # Change node name
    def relabelNode(self, oldNode, newNode):
        if self.G.has_node(oldNode):
            self.G.add_node(newNode, self.G.node[oldNode])
            self.G.remove_node(oldNode)
        self.nodes = nx.nodes(self.G)

    # Check if node exists
    def is_node(self, node):
        return self.G.has_node(node)

    # Getter for nodes and edges
    def getNodes(self):
        return self.nodes
    def getEdges(self):
        return self.edges


    #set all the properties with this function.
    def set_property(self):
        self.clustering()
        self.latapy_clustering()
        self.robins_alexander_clustering()
        self.closeness_centrality()
        self.betweenness_centrality()
        self.degree_centrality()
        self.katz_centrality()
        self.eigenvector_centrality()
        self.load_centrality()
        self.communicability_centrality()
        self.communicability_centrality_exp()

    # Find clustering coefficient for each nodes
    def clustering(self):
        self.clustering_dict = bi.clustering(self.G)
    # set lapaty clustering to empty dictionary if there are more then 2 nodesets
    # else return lapaty clustering coefficients for each nodes
    def latapy_clustering(self):
        if len(self.nodeSet) != 2 or len(set(self.nodeSet)) != 2:
            self.latapy_clustering_dict = {}
        else:
            self.latapy_clustering_dict = bi.latapy_clustering(self.G)
    def robins_alexander_clustering(self):
        self.robins_alexander_clustering_dict = bi.robins_alexander_clustering(self.G)
    # Find closeness_centrality coefficient for each nodes
    def closeness_centrality(self):
        self.closeness_centrality_dict = bi.closeness_centrality(self.G, self.nodes)
    # Find degree_centrality coefficient for each nodes
    def degree_centrality(self):
        self.degree_centrality_dict = nx.degree_centrality(self.G)
    # Find betweenness_centrality coefficient for each nodes
    def betweenness_centrality(self):
        self.betweenness_centrality_dict = nx.betweenness_centrality(self.G)
    def eigenvector_centrality(self):
        self.eigenvector_centrality_dict = nx.eigenvector_centrality(self.G, max_iter=500, tol=1e-01)
    def katz_centrality(self):
        self.katz_centrality_dict = centrality.katz_centrality(self.G)
    def load_centrality(self):
        self.load_centrality_dict = nx.load_centrality(self.G)
    def communicability_centrality(self):
        self.communicability_centrality_dict = nx.communicability_centrality(self.G)
    def communicability_centrality_exp(self):
        self.communicability_centrality_exp_dict = nx.communicability_centrality(self.G)
    def node_attributes(self):
        self.node_attributes_dict = self.G.node
    def get_node_attributes(self,node):
        return self.G.node[node]
    def get_eigenvector_centrality(self, lst=[]):
        if len(lst) == 0:
            return self.eigenvector_centrality_dict
        else:
            sub_dict={}
            for key,value in self.clustering_dict:
                if key in lst:
                    sub_dict[key] = value
            return sub_dict
    def get_clustering(self, lst=[]):
        if len(lst) == 0:
            return self.clustering_dict
        else:
            sub_dict = {}
            for key,value in self.clustering_dict:
                if key in lst:
                    sub_dict[key] = value
            return sub_dict
    def get_latapy_clustering(self, lst=[]):
        if len(lst) == 0:
            return self.latapy_clustering_dict
        else:
            sub_dict={}
            for key, value in self.latapy_clustering_dict:
                if key in lst:
                    sub_dict[key] = value
            return sub_dict
    def get_robins_alexander_clustering(self, lst=[]):
        if len(lst) == 0:
            return self.robins_alexander_clustering_dict
        else:
            sub_dict={}
            for key, value in self.robins_alexander_clustering_dict:
                if key in lst:
                    sub_dict[key] = value
            return sub_dict
    def get_closeness_centrality(self, lst=[]):
        if len(lst) == 0:
            return self.closeness_centrality_dict
        else:
            sub_dict = {}
            for key, value in self.closeness_centrality_dict:
                if key in lst:
                    sub_dict[key] = value
            return sub_dict
    def get_degree_centrality(self, lst=[]):
        if len(lst) == 0:
            return self.degree_centrality_dict
        else:
            sub_dict = {}
            for key, value in self.degree_centrality_dict:
                if key in lst:
                    sub_dict[key] = value
            return sub_dict
    def get_betweenness_centrality(self, lst=[]):
        if len(lst) == 0:
            return self.betweenness_centrality_dict
        else:
            sub_dict = {}
            for key, value in self.betweenness_centrality_dict:
                if key in lst:
                    sub_dict[key] = value
            return sub_dict
    def get_katz_centrality(self, lst=[]):
        if len(lst) == 0:
            return self.katz_centrality_dict
        else:
            sub_dict = {}
            for key, value in self.katz_centrality_dict:
                if key in lst:
                    sub_dict[key] = value
            return sub_dict
    def get_load_centrality(self, lst=[]):
        if len(lst) == 0:
            return self.load_centrality_dict
        else:
            sub_dict = {}
            for key, value in self.load_centrality_dict:
                if key in lst:
                    sub_dict[key] = value
            return sub_dict
    def get_communicability_centrality(self, lst=[]):
        if len(lst) == 0:
            return self.load_centrality_dict
        else:
            sub_dict = {}
            for key, value in self.load_centrality_dict:
                if key in lst:
                    sub_dict[key] = value
            return sub_dict
    def get_communicability_centrality_exp(self, lst=[]):
        if len(lst) == 0:
            return self.communicability_centrality_dict
        else:
            sub_dict = {}
            for key, value in self.communicability_centrality_dict:
                if key in lst:
                    sub_dict[key] = value
            return sub_dict
    # draw 2D graph
    # attr is a dictionary that has color and size as its value.
    def graph_2D(self, attr, label=False):
        block = nx.get_node_attributes(self.G, 'block')
        Nodes = nx.nodes(self.G)
        pos = nx.spring_layout(self.G)
        labels = {}
        for node in block:
            labels[node] = node
        for node in set(self.nodeSet):
            nx.draw_networkx_nodes(self.G, pos,
                                   with_labels=False,
                                   nodelist = [n for n in Nodes if bipartite[n] == node],
                                   node_color = attr[node][0],
                                   node_size = attr[node][1],
                                   alpha=0.8)
        nx.draw_networkx_edges(self.G, pos, width=1.0, alpha=0.5)
        for key,value in pos.items():
            pos[key][1] += 0.01
        if label == True:
            nx.draw_networkx_labels(self.G, pos, labels, font_size=8)
        limits=plt.axis('off')
        plt.show()

    #draw 3 dimensional verison of the graph (returning html object)
    def graph_3D(self):
        n = nx.edges(self.G)
        removeEdge=[]
        for i in range(len(n)):
            if n[i][0] == '' or n[i][1] == '':
                removeEdge.append(n[i])
        for j in range(len(removeEdge)):
            n.remove(removeEdge[j])
        jgraph.draw(nx.edges(self.G), directed="true")

    #note: this is for Vinay's UI
    def plot_2D(self, attr, label=False):
        #print("attr", attr)
        plt.clf()
        block = nx.get_node_attributes(self.G, 'block')
        #print("block",block)
        pos = nx.spring_layout(self.G)
        labels = {}
        for node in block:
            labels[node] = node
            #print("node",node)
        for node in set(self.nodeSet):
            #print("Node",node)
            #print("attr[node]",attr[node])
            nx.draw_networkx_nodes(self.G, pos,
                                   with_labels=False,
                                   nodelist = [key for key, val in block.items() if val == node],
                                   node_color = attr[node][0],
                                   node_size = attr[node][1],
                                   alpha=0.8)
        nx.draw_networkx_edges(self.G, pos, width=1.0, alpha=0.5)
        for key,value in pos.items():
            pos[key][1] += 0.01
        if label == True:
            nx.draw_networkx_labels(self.G, pos, labels, font_size=7)
        plt.axis('off')
        f = tempfile.NamedTemporaryFile(
            dir='static/temp',
            suffix = '.png', delete=False)
        # save the figure to the temporary file
        plt.savefig(f, bbox_inches='tight')
        f.close() # close the file
        # get the file's name
        # (the template will need that)
        plotPng = f.name.split('/')[-1]
        plotPng = plotPng.split('\\')[-1]
        return plotPng

    #create json file for 3 dimensional graph
    #name ex: {name, institution}, {faction leaders, institution}, etc...
    #color: {"0xgggggg", "0xaaaaaa"} etc. (Takes a hexadecimal "String").
    #returns a json dictionary
    def create_json(self, name, color):
        data = {}
        edges = []
        nodes_property = {}
        block = nx.get_node_attributes(self.G, 'block')
        for edge in self.edges:
            edges.append({'source': edge[0], 'target': edge[1], 'name': edge[0] + "," + edge[1]})
        for node, feature in block.items():
            temp = {}
            temp['color'] = color[name.index(feature)]
            nodes_property[node] = temp
        data['edges'] = edges
        data['nodes'] = nodes_property
        return data