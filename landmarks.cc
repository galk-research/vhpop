#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <map>
#include <algorithm>
#include <cctype>

using namespace std;

string trim(const string &s) {
    size_t start = s.find_first_not_of(" \t\r\n");
    if (start == string::npos)
        return "";
    size_t end = s.find_last_not_of(" \t\r\n");
    return s.substr(start, end - start + 1);
}

struct Edge {
    int from;      // source node id
    int to;        // target node id
    string type;   // "gn" or "nat"
};

struct Landmark {
    bool isDisjunctive;
    int id;
    vector<string> atoms;
    vector<Edge> edges;
};


map<int, Landmark> landmarks;

vector<string> get_atoms(string line) {
    vector<string> atomsList;
    size_t posConj = line.find("conj {");
    size_t posDisj = line.find("disj {");
    if(posConj != string::npos || posDisj != string::npos) {
        string atom;
        size_t posAtom = line.find("Atom ");
        size_t posParen = line.find(")", posAtom);
        while (posAtom != string::npos) {
            atomsList.push_back(line.substr(posAtom + 5, posParen - 5 - posAtom + 1));
            posAtom = line.find("Atom ", posParen);
            posParen = line.find(")", posAtom);
        }
    } else {    
        size_t posAtom = line.find("Atom ");
        size_t posParen = line.find(")", posAtom);
        atomsList.push_back(line.substr(posAtom + 5, posParen - 5 - posAtom + 1));
    }
    return atomsList;
}   

int add_landmark(string line) {
    istringstream iss(line);
    string dummy;
    int nodeId;
    iss >> dummy >> nodeId;

    if (line.find("disj") != string::npos) {
        landmarks[nodeId].isDisjunctive = true;
    } else {
        landmarks[nodeId].isDisjunctive = false;
    }
    
    if(landmarks.find(nodeId) == landmarks.end()) {
        landmarks[nodeId] = Landmark();
        landmarks[nodeId].id = nodeId;
    }
    
    string rest;
    getline(iss, rest);
    rest = trim(rest);
    
    landmarks[nodeId].atoms = get_atoms(rest);
    return nodeId;
}

void add_edge(string line, int currentNode) {
    istringstream iss(line);
    string arrowToken;
    iss >> arrowToken;
    
    bool outgoing = false;
    if(arrowToken.substr(0,2) == "<-") {
        return;
    }
    
    size_t underscorePos = arrowToken.find('_');
    string edgeType = "";
    if(underscorePos != string::npos && arrowToken.size() > underscorePos + 1) {
        edgeType = arrowToken.substr(underscorePos + 1);
    }
    
    string lmToken;
    iss >> lmToken;
    int otherNodeId;
    iss >> otherNodeId;
    
    Edge edge;
    edge.from = currentNode;
    edge.to = otherNodeId;
    edge.type = edgeType;
    landmarks[currentNode].edges.push_back(edge);
}

void read_landmarks_file(ifstream &infile) {
    string line;
    bool inGraph = false;
    int currentNodeId = -1;

    while(getline(infile, line)) {
        line = trim(line);
        if(line.empty()) continue;
        
        if(line.find("Landmark graph:") != string::npos) {
            inGraph = true;
            continue;
        }
        if(line.find("Landmark graph end.") != string::npos) {
            break;
        }
        
        if(!inGraph) continue;
        
        // If the line starts with "LM", it is a node definition.
        if(line.size() >= 2 && line.substr(0, 2) == "LM") {
            currentNodeId = add_landmark(line);
        } else {
            add_edge(line, currentNodeId);
        }
    }
    
    infile.close();
}

int main(int argc, char* argv[]) {
    ifstream infile(argv[1]);
    if(!infile) {
        cerr << "Error opening file: " << argv[1] << endl;
        return 1;
    }
    
    string line;
    bool inGraph = false;
    int currentNodeId = -1;

    read_landmarks_file(infile);
    
    cout << "Parsed Nodes:" << endl;
    for(const auto &p : landmarks) {
        cout << "Node LM " << p.first << " with atoms:" << endl;
        for(const auto &atom : p.second.atoms) {
            cout << "    " << atom << endl;
        }
        cout << "Must appear before: " << endl;
        for (const auto &edge : p.second.edges) {
            cout << "    LM " << edge.to << " (" << edge.type << ")" << endl;
        }
    }
    
    return 0;
}
