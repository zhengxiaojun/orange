from OWBaseWidget import *
from OWWidget import OWWidget
import os
import orange, orngTest
from copy import copy
from math import sqrt
import OWGUI, OWDlgs
import OWVisAttrSelection
from OWVisGraph import *

# quality measure
CLASS_ACCURACY = 0
AVERAGE_CORRECT = 1
BRIER_SCORE = 2
ENTROPY_BASED = 3

LEAVE_ONE_OUT = 0
TEN_FOLD_CROSS_VALIDATION = 1
TEST_ON_LEARNING_SET = 2

# results in the list
ACCURACY = 0 
OTHER_RESULTS = 1
LEN_TABLE = 2
ATTR_LIST = 3
TRY_INDEX = 4
STR_LIST = 5

OTHER_ACCURACY = 0
OTHER_PREDICTIONS = 1
OTHER_DISTRIBUTION = 2

ALGORITHM_KNN = 0
ALGORITHM_HEURISTIC = 1

NUMBER_OF_INTERVALS = 6  # number of intervals to use when discretizing 

contMeasures = [("None", None), ("ReliefF", orange.MeasureAttribute_relief(k=10, m=50)), ("Fisher discriminant", OWVisAttrSelection.MeasureFisherDiscriminant()), ("Signal to Noise Ratio", OWVisAttrSelection.S2NMeasure())]
discMeasures = [("None", None), ("ReliefF", orange.MeasureAttribute_relief(k=10, m=50)), ("Gain ratio", orange.MeasureAttribute_gainRatio()), ("Gini index", orange.MeasureAttribute_gini())]


# array of testing methods. used by calling python's apply method depending on the value of self.testingMethod
testingMethods = [orngTest.leaveOneOut, orngTest.crossValidation, orngTest.learnAndTestOnLearnData]

class kNNOptimization(OWBaseWidget):
    EXACT_NUMBER_OF_ATTRS = 0
    MAXIMUM_NUMBER_OF_ATTRS = 1

    settingsList = ["kValue", "resultListLen", "percentDataUsed", "minExamples", "qualityMeasure", "testingMethod",
                    "lastSaveDirName", "attrCont", "attrDisc", "showRank", "showAccuracy", "showInstances",
                    "evaluationAlgorithm", "createSnapshots", "evaluationTimeIndex", "useProjectionValue", "classifierName",
                    "argumentCountIndex", "canUseMoreArguments", "moreArgumentsIndex", "reevaluateProjectionsCount", "reevaluateProjections" ]
    resultsListLenNums = [ 10, 100 ,  250 ,  500 ,  1000 ,  5000 ,  10000, 20000, 50000, 100000, 500000 ]
    percentDataNums = [ 5 ,  10 ,  15 ,  20 ,  30 ,  40 ,  50 ,  60 ,  70 ,  80 ,  90 ,  100 ]
    kNeighboursNums = [ 0 ,  1 ,  2 ,  3 ,  4 ,  5 ,  6 ,  7 ,  8 ,  9 ,  10 ,  12 ,  15 ,  17 ,  20 ,  25 ,  30 ,  40 ,  60 ,  80 ,  100 ,  150 ,  200 ]
    resultsListLenList = [str(x) for x in resultsListLenNums]
    percentDataList = [str(x) for x in percentDataNums]
    kNeighboursList = [str(x) for x in kNeighboursNums]
    argumentCounts = [1, 3, 5, 10, 20, 50, 100, 100000]

    evaluationTimeNums = [0.5, 1, 2, 5, 10, 20, 60, 120]
    evaluationTimeList = [str(x) for x in evaluationTimeNums]

    moreArgumentsNums = [60, 65, 70, 75, 80, 85, 90, 95]
    moreArgumentsList = ["%d %%" % x for x in moreArgumentsNums]

    def __init__(self, parentWidget = None, signalManager = None, graph = None, parentName = "Visualization widget"):
        OWBaseWidget.__init__(self, None, signalManager, "Optimization Dialog")

        self.parentWidget = parentWidget
        self.parentName = parentName
        self.setCaption("Qt VizRank Optimization Dialog")
        self.controlArea = QVBoxLayout(self)

        self.graph = graph
        self.kValue = 10
        self.minExamples = 0
        self.resultListLen = 1000
        self.percentDataUsed = 100
        self.qualityMeasure = 1
        self.testingMethod = 1
        self.optimizationType = 1
        self.attributeCountIndex = 1
        self.canUseMoreArguments = 0
        self.moreArgumentsIndex = 4
        self.evaluationAlgorithm = 0
        self.maxResultListLen = self.resultsListLenNums[len(self.resultsListLenNums)-1]
        self.onlyOnePerSubset = 1    # used in radviz and polyviz
        self.widgetDir = os.path.realpath(os.path.dirname(__file__)) + "/"
        self.lastSaveDirName = os.getcwd()
        self.attrCont = 1
        self.attrDisc = 1
        self.selectedClasses = []
        self.rawdata = None
        self.subsetdata = None
        self.arguments = []
        self.createSnapshots = 1
        self.evaluationTimeIndex = 4
        self.useProjectionValue = 1
        self.reevaluateProjections = 1
        self.reevaluateProjectionsCount = 1000
        self.classifierName = "VizRank learner"

        self.showRank = 0
        self.showAccuracy = 1
        self.showInstances = 0
        self.allResults = []
        self.shownResults = []
        self.attrLenDict = {}
        self.datasetName = ""
        self.dataset = None
        self.cancelOptimization = 0
        self.argumentCountIndex = 1     # when classifying use 10 best arguments
        self.autoSetTheKValue = 1       # automatically set the value k to square root of the number of examples in the data 

        self.loadSettings()

        self.tabs = QTabWidget(self, 'tabWidget')
        self.controlArea.addWidget(self.tabs)
        
        self.MainTab = QVGroupBox(self)
        self.SettingsTab = QVGroupBox(self)
        self.ManageTab = QVGroupBox(self)
        self.ArgumentationTab = QVGroupBox(self)
        self.ClassificationTab = QVGroupBox(self)
        
        
        self.tabs.insertTab(self.MainTab, "Main")
        self.tabs.insertTab(self.SettingsTab, "Settings")
        self.tabs.insertTab(self.ArgumentationTab, "Argumentation")
        self.tabs.insertTab(self.ClassificationTab, "Classification")
        self.tabs.insertTab(self.ManageTab, "Manage & Save")        

        # ###########################
        # MAIN TAB
        self.optimizationBox = OWGUI.widgetBox(self.MainTab, " Evaluate ")
        self.resultsBox = OWGUI.widgetBox(self.MainTab, " Projection List, Most Interesting First ")
        self.resultsDetailsBox = OWGUI.widgetBox(self.MainTab, " Shown Details in Projections List " , orientation = "horizontal")
        self.buttonBox = OWGUI.widgetBox(self.optimizationBox, orientation = "horizontal")
        
        self.label1 = QLabel('Projections with ', self.buttonBox)
        self.optimizationTypeCombo = OWGUI.comboBox(self.buttonBox, self, "optimizationType", items = ["    exactly    ", "  maximum  "] )
        self.attributeCountCombo = OWGUI.comboBox(self.buttonBox, self, "attributeCountIndex", items = [str(x) for x in range(3, 15)] + ["ALL"], tooltip = "Evaluate only projections with exactly (or maximum) this number of attributes")
        self.attributeLabel = QLabel(' attributes', self.buttonBox)

        self.startOptimizationButton = OWGUI.button(self.optimizationBox, self, "Start evaluating projections")
        f = self.startOptimizationButton.font()
        f.setBold(1)
        self.startOptimizationButton.setFont(f)
        self.stopOptimizationButton = OWGUI.button(self.optimizationBox, self, "Stop evaluation", callback = self.stopOptimizationClick)
        self.stopOptimizationButton.setFont(f)
        self.stopOptimizationButton.hide()
        self.optimizeGivenProjectionButton = OWGUI.button(self.optimizationBox, self, "Optimize current projection")
        self.optimizeGivenProjectionButton.hide()

        self.resultList = QListBox(self.resultsBox)
        #self.resultList.setSelectionMode(QListBox.Extended)   # this would be nice if could be enabled, but it has a bug - currentItem doesn't return the correct value if this is on
        self.resultList.setMinimumSize(200,200)

        self.showRankCheck = OWGUI.checkBox(self.resultsDetailsBox, self, 'showRank', 'Rank', callback = self.updateShownProjections, tooltip = "Show projection ranks")
        self.showAccuracyCheck = OWGUI.checkBox(self.resultsDetailsBox, self, 'showAccuracy', 'Predicted Accuracy', callback = self.updateShownProjections, tooltip = "Show prediction accuracy of a k-NN classifier on the projection")
        self.showInstancesCheck = OWGUI.checkBox(self.resultsDetailsBox, self, 'showInstances', '# Instances', callback = self.updateShownProjections, tooltip = "Show number of instances in the projection")

        # ##########################
        # SETTINGS TAB
        self.methodTypeCombo = OWGUI.comboBox(self.SettingsTab, self, "evaluationAlgorithm", box = "Projection evaluation method", tooltip = "Which learning method to use to use to evaluate given projections. \nk nearest neighbor or a very fast but not so perfect heuristic.", items = ["k-Nearest Neighbor", "Heuristic (very fast)"])
        self.optimizationSettingsBox = OWGUI.widgetBox(self.SettingsTab, " Optimization Settings for k-Nearest Neighbors")
        self.heuristicsSettingsBox = OWGUI.widgetBox(self.SettingsTab, " Heuristics for Attribute Ordering ")
        self.miscSettingsBox = OWGUI.widgetBox(self.SettingsTab, " Miscellaneous Settings ")
        #self.miscSettingsBox.hide()
        
        self.attrKNeighboursCombo = OWGUI.comboBoxWithCaption(self.optimizationSettingsBox, self, "kValue", "Number of neighbors (k):                ", tooltip = "Number of neighbors used in k-NN algorithm to evaluate the projection", items = self.kNeighboursNums, sendSelectedValue = 1, valueType = int)
        self.percentDataUsedCombo= OWGUI.comboBoxWithCaption(self.optimizationSettingsBox, self, "percentDataUsed", "Percent of data used in evaluation: ", items = self.percentDataNums, sendSelectedValue = 1, valueType = int)

        self.measureCombo = OWGUI.comboBox(self.optimizationSettingsBox, self, "qualityMeasure", box = " Measure of Classification Success ", items = ["Classification accuracy", "Average probability assigned to the correct class", "Brier score"], tooltip = "Measure to evaluate prediction accuracy of k-NN method on the projected data set.")
        self.testingCombo = OWGUI.comboBox(self.optimizationSettingsBox, self, "testingMethod", box = " Testing Method ", items = ["Leave one out (slowest, most accurate)", "10 fold cross validation", "Test on learning set (fastest, least accurate)"], tooltip = "Method for evaluating the classifier. Slower are more accurate while faster give only a rough approximation.")

        OWGUI.comboBox(self.heuristicsSettingsBox, self, "attrCont", box = " Ordering of Continuous Attributes", items = [val for (val, m) in contMeasures])
        OWGUI.comboBox(self.heuristicsSettingsBox, self, "attrDisc", box = " Ordering of Discrete Attributes", items = [val for (val, m) in discMeasures])

        self.resultListCombo = OWGUI.comboBoxWithCaption(self.miscSettingsBox, self, "resultListLen", "Maximum length of projection list:   ", tooltip = "Maximum length of the list of interesting projections. This is also the number of projections that will be saved if you click Save button.", items = self.resultsListLenNums, callback = self.updateShownProjections, sendSelectedValue = 1, valueType = int)
        self.minTableLenEdit = OWGUI.lineEdit(self.miscSettingsBox, self, "minExamples", "Minimum examples in data set:        ", orientation = "horizontal", tooltip = "Due to missing values, different subsets of attributes can have different number of examples. Projections with less than this number of examples will be ignored.", valueType = int)

        # ##########################
        # SAVE & MANAGE TAB
        self.classesBox = OWGUI.widgetBox(self.ManageTab, " Select class values you wish to separate ")
        self.visualizedAttributesBox = OWGUI.widgetBox(self.ManageTab, " Number of concurrently visualized attributes ")        
        self.manageResultsBox = OWGUI.widgetBox(self.ManageTab, " Manage Projections ")        
        
        self.classesList = QListBox(self.classesBox)
        self.classesList.setSelectionMode(QListBox.Multi)
        self.classesList.setMinimumSize(60,60)
        self.connect(self.classesList, SIGNAL("selectionChanged()"), self.classesListChanged)
        
        self.attrLenList = QListBox(self.visualizedAttributesBox)
        self.attrLenList.setSelectionMode(QListBox.Multi)
        self.attrLenList.setMinimumSize(60,60)
        self.connect(self.attrLenList, SIGNAL("selectionChanged()"), self.attrLenListChanged)
        
        #self.removeSelectedButton = OWGUI.button(self.buttonBox5, self, "Remove selection", self.removeSelected)
        #self.filterButton = OWGUI.button(self.buttonBox5, self, "Save best graphs", self.exportMultipleGraphs)

        self.buttonBox6 = OWGUI.widgetBox(self.manageResultsBox, orientation = "horizontal")
        self.loadButton = OWGUI.button(self.buttonBox6, self, "Load", self.load)
        self.saveButton = OWGUI.button(self.buttonBox6, self, "Save", self.save)

        self.buttonBox7 = OWGUI.widgetBox(self.manageResultsBox, orientation = "horizontal")
        self.graphProjectionsButton = OWGUI.button(self.buttonBox7, self, "Graph projections", self.graphProjectionQuality)
        self.closeButton = OWGUI.button(self.buttonBox7, self, "Result Analysis", self.resultAnalysis)

        self.buttonBox3 = OWGUI.widgetBox(self.manageResultsBox, orientation = "horizontal")
        self.evaluateProjectionButton = OWGUI.button(self.buttonBox3, self, 'Evaluate projection')
        self.reevaluateResults = OWGUI.button(self.buttonBox3, self, "Reevaluate projections", callback = self.reevaluateAllProjections)

        self.buttonBox4 = OWGUI.widgetBox(self.manageResultsBox, orientation = "horizontal")
        self.showKNNCorrectButton = OWGUI.button(self.buttonBox4, self, 'Show k-NN correct')
        self.showKNNWrongButton = OWGUI.button(self.buttonBox4, self, 'Show k-NN wrong')
        self.showKNNCorrectButton.setToggleButton(1); self.showKNNWrongButton.setToggleButton(1)

        self.buttonBox5 = OWGUI.widgetBox(self.manageResultsBox, orientation = "horizontal")
        self.saveBestButton = OWGUI.button(self.buttonBox5, self, "Save best graphs", self.exportMultipleGraphs)
        self.clearButton = OWGUI.button(self.buttonBox5, self, "Clear results", self.clearResults)
        
        # ##########################
        # ARGUMENTATION TAB
        self.argumentationBox = OWGUI.widgetBox(self.ArgumentationTab, " Arguments ")
        self.findArgumentsButton = OWGUI.button(self.argumentationBox, self, "Find arguments", callback = self.findArguments)
        f = self.findArgumentsButton.font(); f.setBold(1);  self.findArgumentsButton.setFont(f)
        self.stopArgumentationButton = OWGUI.button(self.argumentationBox, self, "Stop searching", callback = self.stopArgumentationClick)
        self.stopArgumentationButton.setFont(f)
        self.stopArgumentationButton.hide()
        self.createSnapshotCheck = OWGUI.checkBox(self.argumentationBox, self, 'createSnapshots', 'Create snapshots of projections (a bit slower)', tooltip = "Show each argument with a projections screenshot.\nTakes a bit more time, since the projection has to be created.")
        self.classValueList = OWGUI.comboBox(self.ArgumentationTab, self, "argumentationClassValue", box = " Arguments for class: ", tooltip = "Select the class value that you wish to see arguments for", callback = self.argumentationClassChanged)
        self.argumentBox = OWGUI.widgetBox(self.ArgumentationTab, " Arguments for the selected class value ")
        self.argumentList = QListBox(self.argumentBox)
        self.argumentList.setMinimumSize(200,200)
        self.connect(self.argumentList, SIGNAL("selectionChanged()"),self.argumentSelected)

        # ##########################
        # CLASSIFICATION TAB
        self.classifierNameEdit = OWGUI.lineEdit(self.ClassificationTab, self, 'classifierName', box = ' Learner / Classifier Name ', tooltip='Name to be used by other widgets to identify your learner/classifier.')
        self.useProjectionValueCheck = OWGUI.checkBox(self.ClassificationTab, self, "useProjectionValue", "Use projection value when voting", box = "Voting for class value", tooltip = "Does each projection count for 1 vote or is it dependent on the value of the projection", callback = self.updateClassifierChanges)

        reevalBox = OWGUI.widgetBox(self.ClassificationTab, " Reevaluate projections ")
        self.reevaluateProjectionsCheck = OWGUI.checkBox(reevalBox, self, "reevaluateProjections", "Reevaluate projections for each learning data set", tooltip = "Do you want to reevaluate projections for each learning data set. \nOtherwise, the same projections will be used in the prediction for each test data set.")
        self.reevaluateProjectionsCountCombo = OWGUI.comboBoxWithCaption(reevalBox, self, "reevaluateProjectionsCount", "Number of best projections to reevaluate:  ", tooltip = "How many of the best projections do you want to reevaluate when a new learning data set comes?", items = [1, 10, 100, 250, 500, 1000], sendSelectedValue = 1, valueType = int)

        self.evaluationTimeEdit = OWGUI.comboBoxWithCaption(self.ClassificationTab, self, "evaluationTimeIndex", "Time for evaluating projections (minutes): ", box = "Evaluating time", tooltip = "What is the maximum time that the classifier is allowed for evaluating projections (learning)", items = self.evaluationTimeList)
        projCountBox = OWGUI.widgetBox(self.ClassificationTab, " Argument count ")
        self.argumentCountEdit = OWGUI.comboBoxWithCaption(projCountBox, self, "argumentCountIndex", "Maximum number of arguments used when classifying: ", tooltip = "What is the maximum number of arguments that will be used when classifying an example.", items = ["1", "5", "10", "20", "50", "100", "All"], callback = self.updateClassifierChanges)
        projCountBox2 = OWGUI.widgetBox(projCountBox, orientation = "horizontal")
        self.canUseMoreArgumentsCheck = OWGUI.checkBox(projCountBox2, self, "canUseMoreArguments", "Use additional projections until probability at least: ", tooltip = "If checked, it will allow the classifier to use more arguments when it is not confident enough in the prediction.\nIt will use additional arguments until the predicted probability of one class value will be at least as much as specified in the combo box")
        self.moreArgumentsCombo = OWGUI.comboBox(projCountBox2, self, "moreArgumentsIndex", items = self.moreArgumentsList, tooltip = "If checked, it will allow the classifier to use more arguments when it is not confident enough in the prediction.\nIt will use additional arguments until the predicted probability of one class value will be at least as much as specified in the combo box")

        self.statusBar = QStatusBar(self)
        self.controlArea.addWidget(self.statusBar)
        self.controlArea.activate()

        self.connect(self.classifierNameEdit, SIGNAL("textChanged(const QString &)"), self.classifierNameChanged)
        self.vizRankLearner = VizRankLearner(self, self.parentWidget)
        if self.parentWidget: self.parentWidget.send("VizRank learner", self.vizRankLearner, 0)

        self.resize(375,550)
        self.setMinimumWidth(375)
        self.tabs.setMinimumWidth(375)
        
    # ##############################################################
    # EVENTS
    # ##############################################################
    # when text of vizrank or cluster learners change update their name
    def classifierNameChanged(self, text):
        self.vizRankLearner.name = self.classifierName

    def updateClassifierChanges(self):
        #self.vizRankLearner.classifier = None   # clear the existing classifier, so that there will be a new classifier created
        if self.parentWidget:
            self.parentWidget.send("VizRank learner", self.vizRankLearner, 0)

    # result list can contain projections with different number of attributes
    # user clicked in the listbox that shows possible number of attributes of result list
    # result list must be updated accordingly
    def attrLenListChanged(self):
        # check which attribute lengths do we want to show
        self.attrLenDict = {}
        for i in range(self.attrLenList.count()):
            intVal = int(str(self.attrLenList.text(i)))
            selected = self.attrLenList.isSelected(i)
            self.attrLenDict[intVal] = selected
        self.updateShownProjections()

    def classesListChanged(self):
        results = self.allResults
        self.clearResults()

        self.selectedClasses = self.getSelectedClassValues()
        if len(self.selectedClasses) in [self.classesList.count(), 0]:
            for result in results:
                self.addResult(result[OTHER_RESULTS][0], result[OTHER_RESULTS], result[LEN_TABLE], result[ATTR_LIST], result[TRY_INDEX], result[STR_LIST])
        else: 
            for result in results:
                acc = 0.0; sum = 0.0
                for index in self.selectedClasses:
                    acc += result[OTHER_RESULTS][OTHER_PREDICTIONS][index] * result[OTHER_RESULTS][OTHER_DISTRIBUTION][index]; sum += result[OTHER_RESULTS][OTHER_DISTRIBUTION][index]
                self.addResult(acc/sum, result[OTHER_RESULTS], result[LEN_TABLE], result[ATTR_LIST], result[TRY_INDEX], result[STR_LIST])
                
        self.finishedAddingResults()

    def clearResults(self):
        del self.allResults; self.allResults = []
        del self.shownResults; self.shownResults = []
        self.resultList.clear()
        self.attrLenDict = {}
        self.attrLenList.clear()

    def clearArguments(self):
        del self.arguments; self.arguments = []
        self.argumentList.clear()

    # remove projections that are selected
    def removeSelected(self):
        for i in range(self.resultList.count()-1, -1, -1):
            if self.resultList.isSelected(i):
                # remove from listbox and original list of results
                self.resultList.removeItem(i)
                self.shownResults.remove(self.shownResults[i])


    # ##############################################################
    # ##############################################################

    def getSelectedClassValues(self):
        selectedClasses = []
        for i in range(self.classesList.count()):
            if self.classesList.isSelected(i): selectedClasses.append(i)
        return selectedClasses


    def updateShownProjections(self, *args):
        self.resultList.clear()
        self.shownResults = []
        i = 0

        while self.resultList.count() < self.resultListLen and i < len(self.allResults):
            if self.attrLenDict[len(self.allResults[i][ATTR_LIST])] == 1:
                string = ""
                if self.showRank: string += str(i+1) + ". "
                if self.showAccuracy: string += "%.2f" % (self.allResults[i][ACCURACY])
                if not self.showInstances and self.showAccuracy: string += " : "
                elif self.showInstances: string += " (%d) : " % (self.allResults[i][LEN_TABLE])

                if self.allResults[i][STR_LIST] != "": string += self.allResults[i][STR_LIST]
                else: string += self.buildAttrString(self.allResults[i][ATTR_LIST])
                
                self.resultList.insertItem(string)
                self.shownResults.append(self.allResults[i])
            i+=1
        qApp.processEvents()
        if self.resultList.count() > 0: self.resultList.setCurrentItem(0)        

    # set value of k to sqrt(n)
    def setData(self, data):
        if hasattr(data, "name"): self.datasetName = data.name
        else: self.datasetName = ""
        sameDomain = 0
        if self.rawdata and data and self.rawdata.domain == data.domain: sameDomain = 1
        self.rawdata = data
        self.clearArguments()
        if not sameDomain: self.clearResults()
        
        if not data or not (data.domain.classVar and data.domain.classVar.varType == orange.VarTypes.Discrete):
            self.classesList.clear()
            self.classValueList.clear()
            self.selectedClasses = []
            return

        if self.autoSetTheKValue:
            correct = sqrt(len(data)); i=0
            #set value of k to square root of number of instances in dataset
            while i < len(self.kNeighboursNums) and self.kNeighboursNums[i] < correct: i+=1
            if i==0: self.kValue = self.kNeighboursNums[0]
            else: self.kValue = self.kNeighboursNums[i-1]

        if not sameDomain:
            self.classesList.clear()
            self.classValueList.clear()
            self.selectedClasses = []

            # add class values
            for i in range(len(data.domain.classVar.values)):
                self.classesList.insertItem(data.domain.classVar.values[i])
                self.classValueList.insertItem(data.domain.classVar.values[i])
            self.classesList.selectAll(1)
            if len(data.domain.classVar.values) > 0: self.classValueList.setCurrentItem(0)


    # save subsetdata. first example from this dataset can be used with argumentation - it can find arguments for classifying the example to the possible class values
    def setSubsetData(self, subsetdata):
        self.subsetdata = subsetdata
        self.clearArguments()
    
                
    # given a dataset return a list of (val, attrName) where val is attribute "importance" and attrName is name of the attribute
    # class values that are not interesting for separation (indices not present in self.selectedClasses) are joined in one class value, so
    # that attributes are evaluated based on the interesting class values
    def getEvaluatedAttributes(self, data):
        self.setStatusBarText("Evaluating attributes...")
        selectedClassesStr = [data.domain.classVar.values[i] for i in self.selectedClasses]
        nonSelectedClassesStr = []
        for val in data.domain.classVar.values:
            if val not in selectedClassesStr: nonSelectedClassesStr.append(val)

        if len(nonSelectedClassesStr) > 0:
            selection = orange.EnumVariable("Selection", values = selectedClassesStr + ["nonSelectedClass"])

            shortData1 = data.select({data.domain.classVar.name: selectedClassesStr})
            shortData2 = data.select({data.domain.classVar.name: nonSelectedClassesStr})

            selection.getValueFrom = lambda ex, what: ex[data.domain.classVar]
            d1 = orange.Domain(shortData1.domain.attributes + [selection])
            data1 = orange.ExampleTable(d1, shortData1)

            selection.getValueFrom = lambda ex, what: orange.Value(selection, "nonSelectedClass")
            data2 = orange.ExampleTable(d1, shortData2)
            data1.extend(data2)
            data = data1
        
        attrs = OWVisAttrSelection.evaluateAttributes(data, contMeasures[self.attrCont][1], discMeasures[self.attrDisc][1])
        self.setStatusBarText("")
        return attrs

    
    def addResult(self, accuracy, other_results, lenTable, attrList, tryIndex, strList = ""):
        if self.getQualityMeasure() != BRIER_SCORE: funct = max
        else: funct = min
        self.insertItem(accuracy, other_results, lenTable, attrList, self.findTargetIndex(accuracy, funct), tryIndex, strList)
        qApp.processEvents()        # allow processing of other events

    # use bisection to find correct index
    def findTargetIndex(self, accuracy, funct):
        top = 0; bottom = len(self.allResults)

        while (bottom-top) > 1:
            mid  = (bottom + top)/2
            if funct(accuracy, self.allResults[mid][ACCURACY]) == accuracy: bottom = mid
            else: top = mid

        if len(self.allResults) == 0: return 0
        if funct(accuracy, self.allResults[top][ACCURACY]) == accuracy:
            return top
        else: 
            return bottom

    # insert new result - give parameters: accuracy of projection, number of examples in projection and list of attributes.
    # parameter strList can be a pre-formated string containing attribute list (used by polyviz)
    def insertItem(self, accuracy, other_results, lenTable, attrList, index, tryIndex, strList = ""):
        if index < self.maxResultListLen:
            self.allResults.insert(index, (accuracy, other_results, lenTable, attrList, tryIndex, strList))
        if index < self.resultListLen:
            string = ""
            if self.showRank: string += str(index+1) + ". "
            if self.showAccuracy: string += "%.2f" % (accuracy)
            if not self.showInstances and self.showAccuracy: string += " : "
            elif self.showInstances: string += " (%d) : " % (lenTable)

            if strList != "": string += strList
            else: string += self.buildAttrString(attrList)

            self.resultList.insertItem(string, index)
            self.shownResults.insert(index, (accuracy, lenTable, other_results, attrList, tryIndex, strList))

        # remove worst projection if list is too long
        if self.resultList.count() > self.resultListLen:
            self.resultList.removeItem(self.resultList.count()-1)
            self.shownResults.pop()
    
    def finishedAddingResults(self):
        self.cancelOptimization = 0
        
        self.attrLenList.clear()
        self.attrLenDict = {}
        maxLen = -1
        for i in range(len(self.shownResults)):
            if len(self.shownResults[i][ATTR_LIST]) > maxLen:
                maxLen = len(self.shownResults[i][ATTR_LIST])
        if maxLen == -1: return
        if maxLen == 2: vals = [2]
        else: vals = range(3, maxLen+1)
        for val in vals:
            self.attrLenList.insertItem(str(val))
            self.attrLenDict[val] = 1
        self.attrLenList.selectAll(1)
        self.resultList.setCurrentItem(0)

   
    # ##############################################################
    # ##############################################################
    # kNNEvaluate - evaluate class separation in the given projection using a heuristic or k-NN method
    # ##############################################################
    # ##############################################################
    def kNNComputeAccuracy(self, table):
        # ###############################
        # select a subset of the data if necessary
        # ###############################
        percentDataUsed = int(str(self.percentDataUsedCombo.currentText()))
        if percentDataUsed != 100:
            indices = orange.MakeRandomIndices2(table, 1.0-float(percentDataUsed)/100.0)
            testTable = table.select(indices)
        else: testTable = table

        currentClassDistribution = orange.Distribution(testTable.domain.classVar, testTable)
        currentClassDistribution = [int(v) for v in currentClassDistribution]
        prediction = [0.0 for i in range(len(testTable.domain.classVar.values))]
        
        # ###############################
        # do we want to use very fast heuristic
        # ###############################
        if self.evaluationAlgorithm == ALGORITHM_HEURISTIC:
            # if input attributes are continuous (may be discrete for evaluating scatterplots, where we dicretize the whole domain...)
            if testTable.domain[0].varType == orange.VarTypes.Continuous and testTable.domain[1].varType == orange.VarTypes.Continuous:
                discX = orange.EquiDistDiscretization(testTable.domain[0], testTable, numberOfIntervals = NUMBER_OF_INTERVALS)
                discY = orange.EquiDistDiscretization(testTable.domain[0], testTable, numberOfIntervals = NUMBER_OF_INTERVALS)
                testTable = testTable.select([discX, discY, testTable.domain.classVar])

            # create a new attribute that is a cartesian product of the two visualized attributes
            nattr = orange.EnumVariable(values=['i' for i in range(NUMBER_OF_INTERVALS*NUMBER_OF_INTERVALS)])
            nattr.getValueFrom = orange.ClassifierByLookupTable2(nattr, testTable.domain[0], testTable.domain[1])
            for i in range(NUMBER_OF_INTERVALS*NUMBER_OF_INTERVALS): nattr.getValueFrom.lookupTable[i] = i
            
            for dist in orange.ContingencyAttrClass(nattr, testTable):
                dist = list(dist)
                if sum(dist) == 0: continue
                m = max(dist)
                prediction[dist.index(m)] += m * m / float(sum(dist))

            prediction = [val*100.0 for val in prediction]             # turn prediction array into percents
            acc = sum(prediction) / float(len(testTable))               # compute accuracy for all classes
            val = 0.0; s = 0.0
            for index in self.selectedClasses:                          # compute accuracy for selected classes
                val += prediction[index]; s += currentClassDistribution[index]
            for i in range(len(prediction)): prediction[i] /= float(currentClassDistribution[i])    # turn to probabilities
            if percentDataUsed != 100: del testTable
            return val/float(s), (acc, prediction, currentClassDistribution)
        
        # ###############################
        # or we want to use k nearest neighbor algorithm
        # ###############################
        knn = self.createkNNLearner()
        results = apply(testingMethods[self.testingMethod], [[knn], testTable])
        
        # compute classification success using selected measure
        if testTable.domain.classVar.varType == orange.VarTypes.Discrete:
            if self.qualityMeasure == AVERAGE_CORRECT:
                for res in results.results:
                    prediction[res.actualClass] += res.probabilities[0][res.actualClass]
                prediction = [val*100.0 for val in prediction]

            elif self.qualityMeasure == BRIER_SCORE:
                #return orngStat.BrierScore(results)[0], results
                for res in results.results:
                    val = 0
                    for prob in res.probabilities: val += prob*prob
                    val = val - 2*res.probabilities[res.actualClass] + 1
                    prediction[res.actualClass] += val
                
            elif self.qualityMeasure == CLASS_ACCURACY:
                #return 100*orngStat.CA(results)[0], results
                for res in results.results:
                    prediction[res.actualClass] += res.classes[0]==res.actualClass
                for i in range(len(prediction)): prediction[i] *= 100.0
                
            elif self.qualityMeasure == ENTROPY_BASED:
                # compute n/N * sum_i n_i/n * N_i/n_i * P_r_i = n/N * sum_i N_i/n * P_r_i
                pass

            # compute accuracy only for classes that are selected as interesting. other class values do not participate in projection evaluation
            acc = sum(prediction) / float(len(testTable))
            val = 0.0; s = 0.0
            for index in self.selectedClasses:
                val += prediction[index]; s += currentClassDistribution[index]
            for i in range(len(prediction)):
                if currentClassDistribution[i] > 0:
                    prediction[i] /= float(currentClassDistribution[i])    # turn to probabilities
                else:
                    prediction[i] = 0

            if percentDataUsed != 100: del testTable
            del knn, results
            return val/float(s), (acc, prediction, list(currentClassDistribution))
            
        # for continuous class we can't compute brier score and classification accuracy
        else:
            val = 0.0
            for res in results.results:  val += res.probabilities[0].density(res.actualClass)
            val/= float(len(results.results))
            if percentDataUsed != 100: del testTable
            del knn, results
            return 100.0*val, (100.0*val)

        
    # ##############################################################
    # kNNClassifyData - compute classification error for every example in table
    def kNNClassifyData(self, table):
        qApp.processEvents()        # allow processing of other events
        
        knn = orange.kNNLearner(k=self.kValue, rankWeight = 0, distanceConstructor = orange.ExamplesDistanceConstructor_Euclidean(normalize=0))
        results = apply(testingMethods[self.testingMethod], [[knn], table])
            
        returnTable = []
        if table.domain.classVar.varType == orange.VarTypes.Discrete:
            lenClassValues = len(list(table.domain.classVar.values))
            if self.qualityMeasure == AVERAGE_CORRECT:
                for res in results.results:
                    returnTable.append(res.probabilities[0][res.actualClass])
            elif self.qualityMeasure == BRIER_SCORE:
                for res in results.results:
                    sum = 0
                    for val in res.probabilities[0]: sum += val*val
                    returnTable.append((sum + 1 - 2*res.probabilities[0][res.actualClass])/float(lenClassValues))
            elif self.qualityMeasure == CLASS_ACCURACY:
                for res in results.results:
                    returnTable.append(res.probabilities[0][res.actualClass] == max(res.probabilities[0]))
        else:
            # for continuous class we can't compute brier score and classification accuracy
            for res in results.results:
                returnTable.append(res.probabilities[0].density(res.actualClass))

        del knn, results
        return returnTable


    # reevaluate projections in result list with the current VizRank settings (different k value, different measure of classification succes, ...)
    def reevaluateAllProjections(self):
        results = list(self.getShownResults())
        self.clearResults()

        self.parentWidget.progressBarInit()
        self.disableControls()

        testIndex = 0
        strTotal = createStringFromNumber(len(results))
        for (acc, other, tableLen, attrList, tryIndex, strList) in results:
            if self.isOptimizationCanceled(): continue
            testIndex += 1
            self.parentWidget.progressBarSet(100.0*testIndex/float(len(results)))

            accuracy, other_results = self.graph.getProjectionQuality(attrList)            
            self.addResult(accuracy, other_results, tableLen, attrList, tryIndex, strList)
            self.setStatusBarText("Evaluated %s/%s projections..." % (createStringFromNumber(testIndex), strTotal))

        self.setStatusBarText("")
        self.parentWidget.progressBarFinished()
        self.enableControls()
        self.finishedAddingResults()
    
      
    # ##############################################################
    # Loading and saving projection files
    # ##############################################################

    # save the list into a file - filename can be set if you want to call this function without showing the dialog
    def save(self, filename = None):
        if filename == None:
            # get file name
            if self.datasetName != "":
                filename = "%s - %s" % (os.path.splitext(os.path.split(self.datasetName)[1])[0], self.parentName)
            else:
                filename = "%s" % (self.parentName)
            qname = QFileDialog.getSaveFileName( os.path.join(self.lastSaveDirName, filename), "Interesting projections (*.proj)", self, "", "Save Projections")
            if qname.isEmpty(): return
            name = str(qname)
        else:
            name = filename

        # take care of extension
        if os.path.splitext(name)[1] != ".proj":
            name = name + ".proj"

        dirName, shortFileName = os.path.split(name)
        self.lastSaveDirName = dirName

        # open, write and save file
        file = open(name, "wt")
        attrs = ["kValue", "minExamples", "resultListLen", "percentDataUsed", "qualityMeasure", "testingMethod", "parentName", "evaluationAlgorithm"]
        dict = {}
        for attr in attrs: dict[attr] = self.__dict__[attr]
        dict["dataCheckSum"] = self.rawdata.checksum()
        
        file.write("%s\n" % (str(dict)))
        file.write("%s\n" % str(self.selectedClasses))
        for (acc, other_results, lenTable, attrList, tryIndex, strList) in self.shownResults:
            s = "(%.3f, (" % (acc)
            for val in other_results:
                if type(val) == float: s += "%.3f ," % val
                elif type(val) == list:
                    s += "["
                    for el in val:
                        if type(el) == float: s += "%.3f, " % (el)
                        elif type(el) == int: s += "%d, " % (el)
                        else: s += "%s, " % str(el)
                    if s[-2] == ",": s = s[:-2]
                    s += "], "
            if s[-2] == ",": s = s[:-2]
            s += "), %d, %s, %d, '%s')" % (lenTable, str(attrList), tryIndex, strList)
            file.write(s + "\n")
        file.flush()
        file.close()


    # load projections from a file
    def load(self, name = None):
        self.clearResults()
        self.clearArguments()
        if self.rawdata == None:
            QMessageBox.critical(None,'Load','There is no data. First load a data set and then load projection file',QMessageBox.Ok)
            return

        if name == None:
            name = QFileDialog.getOpenFileName( self.lastSaveDirName, "Interesting projections (*.proj)", self, "", "Open Projections")
            if name.isEmpty(): return
            name = str(name)

        dirName, shortFileName = os.path.split(name)
        self.lastSaveDirName = dirName

        file = open(name, "rt")
        settings = eval(file.readline()[:-1])
        if settings.has_key("parentName") and settings["parentName"] != self.parentName:
            QMessageBox.critical( None, "Optimization Dialog", 'Unable to load projection file. It was saved for %s method'%(settings["parentName"]), QMessageBox.Ok)
            file.close()
            return

        if settings.has_key("dataCheckSum") and settings["dataCheckSum"] != self.rawdata.checksum():
            if QMessageBox.information(self, 'VizRank', 'The current data set has a different checksum than the data set that was used to evaluate projections in this file.\nDo you want to continue loading anyway, or cancel?','Continue','Cancel', '', 0,1):
                file.close()
                return

        self.setSettings(settings)

        # find if it was computed for specific class values
        ind = 0
        line = file.readline()[:-1];
        if type(eval(line)) == list:
            selectedClasses = eval(line)
            for i in range(len(self.rawdata.domain.classVar.values)):
                self.classesList.setSelected(i, i in selectedClasses)
            line = file.readline()[:-1]
        else:
            QMessageBox.critical(None,'Old version of projection file','This file was saved with an older version of Optimization Dialog. The new version of dialog offers \nsome additional functionality and therefore you have to compute the projection quality again.',QMessageBox.Ok)
            return
        
        while (line != ""):
            (acc, other_results, lenTable, attrList, tryIndex, strList) = eval(line)
            self.insertItem(acc, other_results, lenTable, attrList, ind, tryIndex, strList)
            line = file.readline()[:-1]
            ind+=1
        file.close()

        # update loaded results
        self.finishedAddingResults()


    # disable all controls while evaluating projections
    def disableControls(self):
        self.startOptimizationButton.hide()
        self.stopOptimizationButton.show()
        self.resultsDetailsBox.setEnabled(0)
        self.optimizeGivenProjectionButton.setEnabled(0)
        self.SettingsTab.setEnabled(0)
        self.ManageTab.setEnabled(0)
        self.ClassificationTab.setEnabled(0)
        self.ArgumentationTab.setEnabled(0)
        
    def enableControls(self):    
        self.startOptimizationButton.show()
        self.stopOptimizationButton.hide()
        self.resultsDetailsBox.setEnabled(1)
        self.optimizeGivenProjectionButton.setEnabled(1)
        self.SettingsTab.setEnabled(1)
        self.ManageTab.setEnabled(1)
        self.ClassificationTab.setEnabled(1)
        self.ArgumentationTab.setEnabled(1)
        
    # ##############################################################
    # exporting multiple pictures
    # ##############################################################
    def exportMultipleGraphs(self):
        (text, ok) = QInputDialog.getText('Qt Graph count', 'How many of the best projections do you wish to save?')
        if not ok: return
        self.bestGraphsCount = int(str(text))

        self.sizeDlg = OWDlgs.OWChooseImageSizeDlg(self.graph)
        self.sizeDlg.disconnect(self.sizeDlg.okButton, SIGNAL("clicked()"), self.sizeDlg.accept)
        self.sizeDlg.connect(self.sizeDlg.okButton, SIGNAL("clicked()"), self.saveToFileAccept)
        self.sizeDlg.exec_loop()

    def saveToFileAccept(self):
        fileName = str(QFileDialog.getSaveFileName("Graph","Portable Network Graphics (*.PNG);;Windows Bitmap (*.BMP);;Graphics Interchange Format (*.GIF)", None, "Save to..", "Save to.."))
        if fileName == "": return
        (fil,ext) = os.path.splitext(fileName)
        ext = ext.replace(".","")
        if ext == "":	
        	ext = "PNG"  	# if no format was specified, we choose png
        	fileName = fileName + ".png"
        ext = ext.upper()

        (fil, extension) = os.path.splitext(fileName)
        size = self.sizeDlg.getSize()
        for i in range(1, min(self.resultList.count(), self.bestGraphsCount+1)):
            self.resultList.setSelected(i-1, 1)
            self.graph.replot()
            name = fil + " (%02d)" % i + extension
            self.sizeDlg.saveToFileDirect(name, ext, size)
        QDialog.accept(self.sizeDlg)

    def resultAnalysis(self):
        dialog = OWResultAnalysis(self, signalManager = self.signalManager)
        dialog.setResults(self.shownResults, VIZRANK)
        dialog.show()


    def graphProjectionQuality(self):
        dialog = OWGraphProjectionQuality(self, signalManager = self.signalManager)
        dialog.setResults(self.allResults, VIZRANK)
        dialog.show()

    # ######################################################
    # Auxiliary functions
    # ######################################################
    def createkNNLearner(self):
        return orange.kNNLearner(k=self.kValue, rankWeight = 0, distanceConstructor = orange.ExamplesDistanceConstructor_Euclidean(normalize=0))
        
    # return a function that is appropriate to find the best projection in a list in respect to the selected quality measure
    def getMaxFunct(self):
        if self.rawdata.domain.classVar.varType == orange.VarTypes.Discrete and self.qualityMeasure != BRIER_SCORE: return max
        else: return min
    
    # from a list of attributes build a nice string with attribute names
    def buildAttrString(self, attrList):
        if len(attrList) == 0: return ""
        strList = attrList[0]
        for item in attrList[1:]:
            strList = strList + ", " + item
        return strList

    def getOptimizationType(self):
        return self.optimizationType

    def getQualityMeasure(self):
        return self.qualityMeasure

    def getQualityMeasureStr(self):
        if self.qualityMeasure ==0: return "Classification accuracy"
        elif self.qualityMeasure==1: return "Average probability of correct classification"
        else: return "Brier score"

    def getAllResults(self):
        return self.allResults

    def getShownResults(self):
        return self.shownResults

    def getSelectedProjection(self):
        if self.resultList.count() == 0: return None
        return self.shownResults[self.resultList.currentItem()]

    def stopOptimizationClick(self):
        self.cancelOptimization = 1

    def isOptimizationCanceled(self):
        return self.cancelOptimization

    def destroy(self, dw, dsw):
        self.saveSettings()


    # ######################################################
    # Argumentation functions
    # ######################################################
    def findArguments(self, selectBest = 1, showClassification = 1, example = None):
        self.cancelArgumentation = 0
        self.clearArguments()
        self.arguments = [[] for i in range(self.classValueList.count())]
        snapshots = self.createSnapshots
        
        if not example and self.subsetdata == None:
            QMessageBox.information( None, "VizRank Argumentation", 'To find arguments you first have to provide a new example that you wish to classify. \nYou can do this by sending the example to the visualization widget through the "Example Subset" signal.', QMessageBox.Ok + QMessageBox.Default)
            return (None,None)
        if len(self.shownResults) == 0:
            QMessageBox.information( None, "VizRank Argumentation", 'To find arguments you first have to evaluate some projections by clicking "Start evaluating projections" in the Main tab.', QMessageBox.Ok + QMessageBox.Default)
            return (None,None)

        if example == None: example = self.subsetdata[0]
        testExample = [self.parentWidget.graph.scaleExampleValue(example, i) for i in range(len(example.domain.attributes))]

        self.findArgumentsButton.hide()
        self.stopArgumentationButton.show()
        if snapshots: self.parentWidget.setMinimalGraphProperties()

        vals = [0.0 for i in range(len(self.arguments))]

        argumentCount = self.argumentCounts[self.argumentCountIndex]
        foundArguments = 0
        for index in range(len(self.allResults)):       # use only best argumentCount projections for argumentation
            if self.cancelArgumentation: break          # user pressed cancel
            # we also stop if we are not allowed to search for more than argumentCount arguments or we are allowed and we have a reliable prediction or we have used a 100 additional arguments
            if foundArguments >= argumentCount and (not self.canUseMoreArguments or (max(vals)*100.0 / sum(vals) > self.moreArgumentsNums[self.moreArgumentsIndex]) or foundArguments >= argumentCount + 100): break

            qApp.processEvents()
            (accuracy, other_results, lenTable, attrList, tryIndex, strList) = self.allResults[index]
            attrVals = [testExample[self.graph.attributeNameIndex[attrList[i]]] for i in range(len(attrList))]
            if "?" in attrVals: continue    # the testExample has a missing value at one of the visualized attributes
            [xTest, yTest] = self.graph.getProjectedPointPosition(attrList, attrVals)
            table = self.graph.createProjectionAsExampleTable([self.graph.attributeNameIndex[attr] for attr in attrList])
            knn = self.createkNNLearner()(table)
            (classValue, prob) = knn(orange.Example(table.domain, [xTest, yTest, "?"]), orange.GetBoth)
            classValue = int(classValue)
            if self.useProjectionValue:
                for i in range(len(prob)): vals[i] += prob[prob.keys()[i]]
            else: vals[classValue] += 1

            pic = None
            if snapshots:            
                # if the point lies inside a cluster -> save this figure into a pixmap
                self.parentWidget.showAttributes(attrList, clusterClosure = None)
                painter = QPainter()
                pic = QPixmap(QSize(120,120))
                painter.begin(pic)
                painter.fillRect(pic.rect(), QBrush(Qt.white)) # make background same color as the widget's background
                self.graph.printPlot(painter, pic.rect())
                painter.flush();  painter.end()

            value = 0.5 * accuracy + 50.0 * prob[classValue]
            ind = self.getArgumentIndex(value, classValue)
            self.arguments[classValue].insert(ind, (pic, value, accuracy, 100.0 * prob[classValue], prob, attrList, index))
            foundArguments += 1
            if classValue == self.classValueList.currentItem():
                if snapshots: self.argumentList.insertItem(pic, "%.2f (%.2f, %.2f) - %s" %(value, accuracy, 100.0*prob[classValue], attrList), ind)
                else:         self.argumentList.insertItem("%.2f (%.2f, %.2f) - %s" %(value, accuracy, 100.0*prob[classValue], attrList), ind)

        self.stopArgumentationButton.hide()
        self.findArgumentsButton.show()
        self.parentWidget.restoreGraphProperties()
        if self.argumentList.count() > 0 and selectBest: self.argumentList.setCurrentItem(0)
        if foundArguments == 0: return (None, None)

        suma = sum(vals)
        dist = orange.DiscDistribution([val/float(suma) for val in vals]);  dist.variable = self.rawdata.domain.classVar
        classValue = example.domain.classVar[vals.index(max(vals))]
        s = '<nobr>Based on current classification settings, the example would be classified </nobr><br><nobr>to class <b>%s</b> with probability <b>%.2f%%</b>.</nobr><br><nobr>Predicted class distribution is:</nobr><br>' % (classValue, dist[classValue]*100)
        for key in dist.keys():
            s += "<nobr>&nbsp &nbsp &nbsp &nbsp %s : %.2f%%</nobr><br>" % (key, dist[key]*100)
        if foundArguments > argumentCount:
            s += "<nobr>Note: To get the current prediction, <b>%d</b> arguments had to be used (instead of %d)<br>" % (foundArguments, argumentCount)
        s = s[:-4]
        #print s
        #if showClassification or (not example[example.domain.classVar.name].isSpecial() and example.getclass().value != classValue):
        #    QMessageBox.information(None, "Classification results", s, QMessageBox.Ok + QMessageBox.Default)
        # TO DO
        return classValue, dist
       
    def getArgumentIndex(self, value, classValue):
        top = 0; bottom = len(self.arguments[classValue])
        while (bottom-top) > 1:
            mid  = (bottom + top)/2
            if max(value, self.arguments[classValue][mid][1]) == value: bottom = mid
            else: top = mid

        if len(self.arguments[classValue]) == 0: return 0
        if max(value, self.arguments[classValue][top][1]) == value:  return top
        else:                                                        return bottom
        
    def stopArgumentationClick(self):
        self.cancelArgumentation = 1
    
    def argumentationClassChanged(self):
        self.argumentList.clear()
        if len(self.arguments) == 0: return
        ind = self.classValueList.currentItem()
        for i in range(len(self.arguments[ind])):
            val = self.arguments[ind][i]
            if val[0] != None:  self.argumentList.insertItem(val[0], "%.2f (%.2f, %.2f) - %s" %(val[1], val[2], val[3], val[4]))
            else:               self.argumentList.insertItem("%.2f (%.2f, %.2f) - %s" %(val[1], val[2], val[3], val[4]))

    def argumentSelected(self):
        ind = self.argumentList.currentItem()
        classInd = self.classValueList.currentItem()
        self.parentWidget.showAttributes(self.arguments[classInd][ind][5], clusterClosure = None)
        
    def setStatusBarText(self, text):
        self.statusBar.message(text)
        qApp.processEvents()

# #############################################################################
# class that represents kNN classifier that classifies examples based on top evaluated projections
class VizRankClassifier(orange.Classifier):
    def __init__(self, kNNOptimizationDlg, visualizationWidget, data, firstTime = 1):
        self.kNNOptimizationDlg = kNNOptimizationDlg
        self.visualizationWidget = visualizationWidget

        results = kNNOptimizationDlg.getAllResults()
        if firstTime and results != None and len(results) > 0:
            computeProjections = QMessageBox.information(kNNOptimizationDlg, 'VizRank classifier', 'Do you want to classify examples based the projections that are currently in the projection list \n or do you want to compute new projections?','Current projections','Compute new projections', '', 0,1)
            #computeProjections = 0
        elif results != None and len(results) > 0:
            computeProjections = 0
        else: computeProjections = 1

        if computeProjections == 1:
            self.evaluating = 1
            self.visualizationWidget.cdata(data, clearResults = 0)
            t = QTimer(self.visualizationWidget)
            self.visualizationWidget.connect(t, SIGNAL("timeout()"), self.stopEvaluation)
            t.start(self.kNNOptimizationDlg.evaluationTimeNums[self.kNNOptimizationDlg.evaluationTimeIndex] * 60 * 1000, 1)
            self.visualizationWidget.optimizeSeparation()
            t.stop()
            self.evaluating = 0
        else:
            self.visualizationWidget.cdata(data, clearResults = 0)
            if self.kNNOptimizationDlg.reevaluateProjections:
                val = self.kNNOptimizationDlg.resultListLen
                self.kNNOptimizationDlg.resultListLen = self.kNNOptimizationDlg.reevaluateProjectionsCount
                self.kNNOptimizationDlg.updateShownProjections()
                self.kNNOptimizationDlg.reevaluateAllProjections()
                self.kNNOptimizationDlg.resultListLen = val

    # timer event that stops evaluation of clusters
    def stopEvaluation(self):
        if self.evaluating:
            self.kNNOptimizationDlg.stopOptimizationClick()
            

    # for a given example run argumentation and find out to which class it most often fall        
    def __call__(self, example, returnType):
        table = orange.ExampleTable(example.domain)
        table.append(example)
        self.visualizationWidget.subsetdata(table, 0)       # comment this!!!
        snapshots = self.kNNOptimizationDlg.createSnapshots
        self.kNNOptimizationDlg.createSnapshots = 0
        classVal, dist = self.kNNOptimizationDlg.findArguments(0, 0, example)
        self.kNNOptimizationDlg.createSnapshots = snapshots

        #del table
        if returnType == orange.GetBoth: return classVal, dist
        else:                            return classVal
        

# #############################################################################
# learner that builds VizRankClassifier
class VizRankLearner(orange.Learner):
    def __init__(self, kNNOptimizationDlg, visualizationWidget):
        self.kNNOptimizationDlg = kNNOptimizationDlg
        self.visualizationWidget = visualizationWidget
        self.name = self.kNNOptimizationDlg.classifierName
        self.firstTime = 1
        
        
    def __call__(self, examples, weightID = 0):
        classifier = VizRankClassifier(self.kNNOptimizationDlg, self.visualizationWidget, examples, self.firstTime)
        self.firstTime = 0
        return classifier



VIZRANK = 0
CLUSTER = 1

# #############################################################################
# analyse the attributes that appear in the top projections. show how often do they appear also in other top projections
class OWResultAnalysis(OWWidget):
    def __init__(self,parent=None, signalManager = None):
        OWWidget.__init__(self, parent, signalManager, "Result Analysis", wantGraph = 1)

        self.attributeCount = 10
        self.projectionCount = 50
        self.rotateXAttributes = 1
        self.onlyLower = 1
        self.results = None
        self.dialogType = -1

        self.graph = OWVisGraph(self.mainArea)
        self.box = QVBoxLayout(self.mainArea)
        self.box.addWidget(self.graph)
        self.box.activate()

        self.connect(self.graphButton, SIGNAL("clicked()"), self.graph.saveToFile)

        OWGUI.hSlider(self.controlArea, self, 'attributeCount', box='Number Of Attributes', minValue=5, maxValue = 200, step=1, callback = self.updateGraph, ticks=5)
        self.projectionCountSlider = OWGUI.hSlider(self.controlArea, self, 'projectionCount', box='Number Of Projections', minValue=1, maxValue = 100000, step=1, callback = self.updateGraph, ticks=5)
        OWGUI.checkBox(self.controlArea, self, 'rotateXAttributes', label = "Rotate X Labels", box = 1, callback = self.updateGraph)
        OWGUI.checkBox(self.controlArea, self, 'onlyLower', label = "Show Only Lower Diagonal", box = 1, callback = self.updateGraph)
        box = OWGUI.widgetBox(self.controlArea, box = 1)
        box.setSizePolicy(QSizePolicy(QSizePolicy.Minimum , QSizePolicy.MinimumExpanding ))
        
        self.updateGraph()

    def setResults(self, results, dialogType):
        self.results = results
        self.dialogType = dialogType
        if results:
            self.projectionCountSlider.setMaxValue(len(results))
            self.projectionCountSlider.setTickInterval(len(results)/10)
        else: self.projectionCountSlider.setMaxValue(1)
        self.updateGraph()

    def updateGraph(self):
        black = QColor(0,0,0)
        white = QColor(255,255,255)
        self.graph.clear()
        self.graph.removeMarkers()
        if self.results == None or  self.dialogType not in [VIZRANK, CLUSTER]: return

        attributes = []
        attrDict = {}
        index = 0; projectionsUsed = 0

        while index < len(self.results):
            if projectionsUsed >= self.projectionCount: break
            projectionsUsed += 1
            
            attrs = []
            if self.dialogType == VIZRANK:
                if index >= len(self.results): break
                attrs = self.results[index][3]
                index += 1
            else:
                while index < len(self.results) and type(self.results[index][4]) != dict: index += 1
                if index >= len(self.results): break
                attrs = self.results[index][3]
                index += 1

            if len(attributes) < self.attributeCount:
                for attr in attrs:
                    if attr not in attributes and len(attributes) < self.attributeCount:
                        attributes.append(attr)

            for i in range(len(attrs)):
                for j in range(i+1, len(attrs)):
                    if attrs[i] not in attributes or attrs[j] not in attributes: continue
                    if not attrDict.has_key((attrs[i], attrs[j])) and not attrDict.has_key((attrs[j], attrs[i])):
                        attrDict[(attrs[i], attrs[j])] = 1
                        if attrs[i] not in attributes: attributes.append(attrs[i])
                        if attrs[j] not in attributes: attributes.append(attrs[j])
   
        eps = 0.05
        num = len(attributes)
        #for x in range(num-1):
        #    for y in range(num-x-1):
        for x in range(num):
            for y in range(num-x):
                yy = num-y-1
                if not attrDict.has_key((attributes[x], attributes[yy])) and not attrDict.has_key((attributes[yy], attributes[x])): continue
                
                curve = PolygonCurve(self.graph, QPen(black), QBrush(black))
                key = self.graph.insertCurve(curve)
                self.graph.setCurveData(key, [x+eps, x+1-eps, x+1-eps, x+eps], [y+eps, y+eps, y+1-eps, y+1-eps])

                if not self.onlyLower:
                    curve = PolygonCurve(self.graph, QPen(black), QBrush(black))
                    key = self.graph.insertCurve(curve)
                    self.graph.setCurveData(key, [num-1-y+eps, num-1-y+eps, num-y-eps, num-y-eps], [num-1-x+eps, num-x-eps, num-x-eps, num-1-x+eps] )

        # draw empty boxes at the diagonal
        for x in range(num):
            curve = PolygonCurve(self.graph, QPen(black), QBrush(white))
            key = self.graph.insertCurve(curve)
            self.graph.setCurveData(key, [x+eps, x+1-eps, x+1-eps, x+eps], [num-x-1+eps, num-x-1+eps, num-x-eps, num-x-eps])


        # draw x markers
        for x in range(num):
            if self.rotateXAttributes: marker = MyMarker(self.graph, attributes[x], x + 0.5, -0.3, 90)
            else: marker = MyMarker(self.graph, attributes[x], x + 0.5, -0.3, 0)
            mkey = self.graph.insertMarker(marker)
            if self.rotateXAttributes: self.graph.marker(mkey).setLabelAlignment(Qt.AlignLeft+ Qt.AlignCenter)
            else: self.graph.marker(mkey).setLabelAlignment(Qt.AlignCenter + Qt.AlignBottom)

        # draw y markers
        for y in range(num):
            mkey = self.graph.insertMarker(attributes[num-y-1])
            self.graph.marker(mkey).setXValue(-0.3)
            self.graph.marker(mkey).setYValue(y + 0.5)
            self.graph.marker(mkey).setLabelAlignment(Qt.AlignLeft + Qt.AlignHCenter)

            
            
        self.graph.setAxisScaleDraw(QwtPlot.xBottom, HiddenScaleDraw())
        self.graph.setAxisScaleDraw(QwtPlot.yLeft, HiddenScaleDraw())
        self.graph.axisScaleDraw(QwtPlot.xBottom).setTickLength(0, 0, 0)
        self.graph.axisScaleDraw(QwtPlot.yLeft).setTickLength(0, 0, 0)
        self.graph.axisScaleDraw(QwtPlot.xBottom).setOptions(0) 
        self.graph.axisScaleDraw(QwtPlot.yLeft).setOptions(0) 
        self.graph.setAxisScale(QwtPlot.xBottom, - 1.2 - 0.1*len(attributes) , num, 1)
        self.graph.setAxisScale(QwtPlot.yLeft, - 0.9 - 0.1*len(attributes) , num, 1)
        
        self.graph.update()  # don't know if this is necessary
        self.graph.repaint()
            

# #############################################################################
# draw a graph for all the evaluated projections that shows how is the classification accuracy falling when we are moving from the best to the worst evaluated projections
class OWGraphProjectionQuality(OWWidget):
    def __init__(self,parent=None, signalManager = None):
        OWWidget.__init__(self, parent, signalManager, "Projection Quality", wantGraph = 1)

        self.lineWidth = 1
        OWGUI.comboBox(self.controlArea, self, "lineWidth", box = "Line width", items = range(5), sendSelectedValue = 1, valueType = int)        

        self.graph = OWVisGraph(self.mainArea)
        self.results = None
        self.dialogType = -1
        self.box = QVBoxLayout(self.mainArea)
        self.box.addWidget(self.graph)
        self.box.activate()

        self.connect(self.graphButton, SIGNAL("clicked()"), self.graph.saveToFile)
        self.updateGraph()

    def setResults(self, results, dialogType):
        self.results = results
        self.dialogType = dialogType
        self.updateGraph()

    def updateGraph(self):
        colors = ColorPaletteHSV(2)
        self.graph.clear()
        if self.results == None or self.dialogType not in [VIZRANK, CLUSTER]: return

        yVals = []
        yVals2 = []
        for i in range(len(self.results)):
            if self.dialogType == VIZRANK:
                yVals.append(self.results[i][0])
            else:
                if type(self.results[i][4]) == dict:
                    yVals2.append(self.results[i][0])
                else:
                    yVals.append(self.results[i][0])

        xVals = range(len(yVals))
        if len(yVals) > 10:
            fact = len(yVals)/200
            if fact > 0:        # make the array of data smaller
                pos = 0             
                xTemp = []; yTemp = []
                while pos < len(yVals):
                    xTemp.append(xVals[pos])
                    yTemp.append(yVals[pos])
                    pos += fact
                xVals = xTemp; yVals = yTemp

        #c = QColor(0,0,0)
        c = colors.getColor(0)
        self.graph.addCurve("", c, c, 1, QwtCurve.Lines, QwtSymbol.None, xData = xVals, yData = yVals, lineWidth = self.lineWidth)

        if yVals2 != []:
            c = colors.getColor(1)
            self.graph.addCurve("", c, c, 1, QwtCurve.Lines, QwtSymbol.None, xData = range(len(yVals2)), yData = yVals2, lineWidth = self.lineWidth)

        self.graph.update()  # don't know if this is necessary
        self.graph.repaint()
            


#test widget appearance
if __name__=="__main__":
    import sys
    a=QApplication(sys.argv)
    #ow=kNNOptimization()
    ow = OWResultAnalysis()
    a.setMainWidget(ow)
    ow.show()
    a.exec_loop()
    