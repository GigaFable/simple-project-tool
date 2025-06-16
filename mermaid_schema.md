Stages with no sub-stages are represented by rectangles containing the title on a line, followed by an empty line and then the description (if present).
Stages with sub-stages are represented as sub-graphs (titled with the node title) with a rectangle node at the top with the title and description (if present) of the stage.
Stages which are milestones are represented as hexagons.
Stages that have depends_on set are related with an arrow linking the depended on property to the one depending. They are also ordered in the flow so that all the dependencies are below them in the diagram.
Stages are output in a flowing order from first to last, from the bottom.

Parallel stages flow only to their parent stage.

The top-level stage is represented by a hexagon but is not represented as a sub-graph.
