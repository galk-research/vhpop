#include "landmarks.h"

string trim(const string &s) {
    size_t start = s.find_first_not_of(" \t\r\n");
    if (start == string::npos)
        return "";
    size_t end = s.find_last_not_of(" \t\r\n");
    return s.substr(start, end - start + 1);
}

vector<string> split(const string &s, char delimiter) {
    vector<string> tokens;
    istringstream iss(s);
    string token;
    while(getline(iss, token, delimiter)) {
        tokens.push_back(trim(token));
    }
    return tokens;
}

LandmarkGraph lm_graph;

const Atom get_atom(string line, const PredicateTable& predicateTable, const TermTable& termTable) {
    
    size_t posAtom = line.find("Atom ");
    size_t posLeftParen = line.find("(", posAtom);
    size_t posRightParen = line.find(")", posLeftParen);
    string atom = line.substr(posAtom + 5, posLeftParen - 5 - posAtom);
       
    vector<string> terms = split(line.substr(posLeftParen + 1, posRightParen - posLeftParen - 1), ',');
    vector<Term> termList;
    for(const auto &term : terms) {
        termList.push_back(*termTable.find_object(term));
    }
    return Atom::make(*predicateTable.find_predicate(atom), termList);

}

Formula* get_formula(string line, const Problem& problem) {
    const PredicateTable& predicateTable = problem.domain().predicates();
    const TermTable& termTable = problem.terms();
    
    size_t posConj = line.find("conj {");
    size_t posDisj = line.find("disj {");
    
    if(posConj != string::npos || posDisj != string::npos) {
        vector<Atom> atomsList;
        size_t posAtom = line.find("Atom ");
        while (posAtom != string::npos) {
            atomsList.push_back(get_atom(line, predicateTable, termTable));
            
            line[posAtom] = '$';
            posAtom = line.find("Atom ");
        }

        if(posConj != string::npos) {
            auto* formula = new Conjunction();
            for (const Atom& atom : atomsList) {
                formula->add_conjunct(*new Atom(atom));
            }
            return formula;
        } else {
            auto* formula = new Disjunction();
            for (const Atom& atom : atomsList) {
                formula->add_disjunct(*new Atom(atom));
            }
            return formula;
        }
    } else {  
        size_t posAtom = line.find("NegatedAtom ");
        if(posAtom != string::npos) {
            // return new Negation(get_atom(line, predicateTable, termTable));
            return const_cast<Negation*>(&Negation::make(*new Atom(get_atom(line, predicateTable, termTable))));
        }
        return new Atom(get_atom(line, predicateTable, termTable));
    }
}   

int add_landmark(string line, const Problem& problem) {
    istringstream iss(line);
    string dummy;
    int nodeId;
    iss >> dummy >> nodeId;
    
    string rest;
    getline(iss, rest);
    rest = trim(rest);

    lm_graph.landmarks[nodeId] = Landmark();
    lm_graph.landmarks[nodeId].id = nodeId;
    lm_graph.landmarks[nodeId].formula = get_formula(rest, problem);
    
    lm_graph.num_landmarks++;

    return nodeId;
}

void add_edge(string line, int currentNode) {
    istringstream iss(line);
    string arrowToken;
    iss >> arrowToken;

    if(arrowToken.substr(0,2) == "<-") {
        lm_graph.landmarks[currentNode].is_initial_state = false;
        return;
    } else {
        lm_graph.landmarks[currentNode].is_goal_state = false;
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
    lm_graph.landmarks[currentNode].edges.push_back(edge);
}

void read_landmarks_file(string file_name, const Problem& problem) {
    ifstream infile(file_name);
    if(!infile) {
        cerr << "Error opening file: " << file_name << endl;
        exit(1);
    }

    string line;
    bool in_graph = false;
    int current_node_id = -1;

    while(getline(infile, line)) {
        line = trim(line);
        if(line.empty()) continue;
        
        if(line.find("Landmark graph:") != string::npos) {
            in_graph = true;
            continue;
        }
        if(line.find("Landmark graph end.") != string::npos) {
            break;
        }
        
        if(!in_graph) continue;
        
        // If the line starts with "LM", it is a node definition.
        if(line.size() >= 2 && line.substr(0, 2) == "LM") {
            current_node_id = add_landmark(line, problem);
        } else {
            add_edge(line, current_node_id);
        }
    }
    infile.close();
}