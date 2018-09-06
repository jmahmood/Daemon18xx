18xx's Railway Paths and Graphs
-------------------------------

One of the interesting computer science parts of 18xx is the networked train lines.

Simply put, you establish a rail network and within constraints, you try to extract the maximum benefit from the network.
 There is a lot of route-finding involved, and I think it will make a fun blog post eventually.  
 I'm putting some information in here for those who find this academically interesting.
  
References:
https://en.wikipedia.org/wiki/Graph_theory#Problems
https://en.wikipedia.org/wiki/Breadth-first_search

August 2018

I currently feel that the most conceptually simple solution is as follows.
 
 1. Find all *simple* paths that are valid.
    - A simple path = does not have repeated vertices
    - Path is of length 2, 3, 4, 5 and 6 (Forget diesels for now)
        - Length is the number of cities or towns visited
    - Must contain a station belonging to the company
    - Must start and end in a town

    *Note*: If there are mutually exclusive paths (1-3 or 1-4 but not both, for example), you would have to generate 
    different graphs for each possibility.  This could get painful very quickly.

 2. Create sets of mutually exclusive paths
    - They should not use the same edges to move between nodes in the tree.

 3. For the number of trains available, choose the most valuable path. (The path with the maximum weight?)
 
All 2-length paths should be subsets of 3-length paths and the such.

The way this would probably work is as follows:

- For each station
    - Is there a path / several paths to another city or town node?
        - Store those edges in a set for each path.
        - *Practically speaking, there won't be too many ways to move from city to city in 1830.*
    - Repeat until you cannot progress any further

You have a Set[Set[Edges]], each of which contains a paths to create all of the available paths of length 2, 3, 4, 5 and 6 (where available).

Set[Edges] == Path, so you can simplify the above as Set[Path]

For each set of edges, you can now determine which are mutually exclusive and create a List[Set[Path]].  Each list will contain a set of mutually exclusive paths.  You can ascertain the value of the paths available.

You can then generate a List[Set[Path]]; this contains a set of paths.  each set list will have 1 or more "destination sets", and the monetary value of each one.

You can sum up the monetary value of each set list and, depending on the number / type of trains available, assign the train.

My main concern here is computational efficiency, as I can easily imagine this getting out of control.  I don't see the value of using an algo that is n! and works but slowly becomes unbearably slow.

----------

1. Using BFS from each station, find all valid paths to other cities.
2. Create List[set[Path]]