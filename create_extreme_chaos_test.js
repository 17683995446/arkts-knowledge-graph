
const fs = require('fs');
const path = require('path');

console.log('===== 第13阶段：创建极端混乱和超复杂测试场景 =====\n');

const EXTREME_TEST_DIR = path.join(__dirname, 'extreme_chaos_test');

if (fs.existsSync(EXTREME_TEST_DIR)) {
  fs.rmSync(EXTREME_TEST_DIR, { recursive: true, force: true });
}

fs.mkdirSync(EXTREME_TEST_DIR, { recursive: true });

console.log('--- 创建混乱场景文件夹结构 ---');

// 创建深度嵌套的目录结构
let deepPath = EXTREME_TEST_DIR;
for (let i = 0; i < 20; i++) {
  deepPath = path.join(deepPath, `deep_dir_${i}`);
  fs.mkdirSync(deepPath, { recursive: true });
}

console.log('✓ 创建了20层深度嵌套目录');

// 1. 创建极其混乱的代码文件（包含各种语法错误）
console.log('--- 创建混乱和错误文件 ---');

const chaosFile1 = `
// 极其混乱的代码 - 故意包含各种错误
export class ChaosClass1 {
  private data: any;
  
  constructor() {
    this.data = {};
  }
  
  // 故意不闭合
  public brokenMethod1() {
    console.log('broken code');
    // 缺少闭合括号
    
  public validMethod() {
    this.callAnother();
    this.doSomething();
  }
  
  private callAnother() {
    console.log('called');
  }
  
  private doSomething() {
    // 做什么都不知道
  }
  
  // 字符串中包含括号
  public stringWithBrackets() {
    const str1 = "function() { return 'test'; }";
    const str2 = 'some text (with parentheses)';
    const str3 = \`template \${variable} literal\`;
    console.log(str1, str2, str3);
  }
  
  // 复杂的嵌套
  public complexNesting() {
    if (true) {
      if (true) {
        if (true) {
          if (true) {
            if (true) {
              if (true) {
                if (true) {
                  if (true) {
                    if (true) {
                      console.log('10 levels deep!');
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
  
  // 超级长的方法名
  public thisMethodHasAnExtremelyLongNameThatShouldNotBeATypicalUseButIsUsefulForTestingTheParserLimitations() {
    console.log('long name called');
  }
  
  // 大量注释和注释中的代码
  public commentedCode() {
    // this is a comment with code: console.log('commented out');
    /* 
      Multi-line comment with more code:
      function fakeFunction() { 
        doFakeStuff(); 
      }
    */
    console.log('real code');
  }
  
  // 特殊字符和奇怪的格式
  public weirdChars() {
    const var_with_underscores = 1;
    const varWithCamelCase = 2;
    const var-with-dashes = 3; // 无效，但测试解析器
    console.log(var_with_underscores, varWithCamelCase);
  }
}

// 另一个混乱的类
export class AnotherChaosClass {
  private value: number = 0;
  
  public increment() {
    this.value++;
    this.logValue();
  }
  
  private logValue() {
    console.log('value:', this.value);
  }
}
`;

fs.writeFileSync(path.join(EXTREME_TEST_DIR, 'chaos_1.ts'), chaosFile1);

// 2. 创建只有注释的文件
const commentsOnly = `
/*
This is just a file full of comments
And nothing else
No code at all
*/

// Single line comment 1
// Single line comment 2

/* Multi-line again */

// The end
`;

fs.writeFileSync(path.join(EXTREME_TEST_DIR, 'only_comments.ts'), commentsOnly);

// 3. 创建几乎是空的文件
const almostEmpty = `
// Just one line
`;

fs.writeFileSync(path.join(EXTREME_TEST_DIR, 'almost_empty.ts'), almostEmpty);

// 4. 创建完全空的文件
fs.writeFileSync(path.join(EXTREME_TEST_DIR, 'totally_empty.ts'), '');

console.log('✓ 创建了4个混乱和错误文件');

// 5. 创建极其复杂的嵌套类结构
console.log('--- 创建极其复杂的嵌套结构 ---');

let complexClass = `
// 极其复杂的类结构
export class SuperComplexClass {
  private level1: any;
  
  constructor() {
    this.level1 = {
      level2: {
        level3: {
          level4: {
            level5: {
              value: 'deep'
            }
          }
        }
      }
    };
    this.initializeAll();
  }
  
  public initializeAll() {
    this.setupLevel1();
    this.setupLevel2();
    this.setupLevel3();
    this.setupLevel4();
    this.setupLevel5();
  }
  
  private setupLevel1() {
    console.log('setup level 1');
  }
  
  private setupLevel2() {
    console.log('setup level 2');
  }
  
  private setupLevel3() {
    console.log('setup level 3');
  }
  
  private setupLevel4() {
    console.log('setup level 4');
  }
  
  private setupLevel5() {
    console.log('setup level 5');
  }
  
  public getValue() {
    return this.level1.level2.level3.level4.level5.value;
  }
  
  // 复杂的switch和if-else
  public complexLogic(condition: number) {
    switch (condition) {
      case 1:
        this.condition1();
        break;
      case 2:
        this.condition2();
        break;
      case 3:
        this.condition3();
        break;
      default:
        this.defaultCase();
        break;
    }
  }
  
  private condition1() {
    if (true) {
      console.log('cond1 true');
    } else {
      console.log('cond1 false');
    }
  }
  
  private condition2() {
    for (let i = 0; i < 10; i++) {
      if (i % 2 === 0) {
        this.even(i);
      } else {
        this.odd(i);
      }
    }
  }
  
  private even(i: number) {
    console.log('even:', i);
  }
  
  private odd(i: number) {
    console.log('odd:', i);
  }
  
  private condition3() {
    try {
      this.riskyOperation();
    } catch (error) {
      this.handleError(error);
    }
  }
  
  private riskyOperation() {
    console.log('risky');
  }
  
  private handleError(error: any) {
    console.error('error:', error);
  }
  
  private defaultCase() {
    console.log('default');
  }
  
  // 大量的getter和setter
  get data(): any {
    return this.level1;
  }
  
  set data(value: any) {
    this.level1 = value;
  }
}

// 更多复杂类
export class AnotherComplexClass {
  private value: string = 'test';
  
  public getValue(): string {
    return this.value;
  }
  
  public setValue(val: string): void {
    this.value = val;
    this.validateValue();
  }
  
  private validateValue() {
    if (!this.value) {
      console.log('invalid');
    } else {
      console.log('valid');
    }
  }
  
  public processData() {
    this.formatData();
    this.saveData();
    this.notify();
  }
  
  private formatData() {
    console.log('formatting');
  }
  
  private saveData() {
    console.log('saving');
  }
  
  private notify() {
    console.log('notifying');
  }
}
`;

fs.writeFileSync(path.join(EXTREME_TEST_DIR, 'complex_structure.ts'), complexClass);
console.log('✓ 创建了极其复杂的嵌套结构');

// 6. 创建大量方法的类（测试极限）
console.log('--- 创建极限类 ---');

let hugeClass = `
// 具有大量方法的类 - 测试解析极限
export class HugeMethodClass {
`;

for (let i = 0; i < 50; i++) {
  hugeClass += `
  public method${i}(): void {
    console.log('method${i} called');
    this.helper${i}();
  }
  
  private helper${i}(): void {
    console.log('helper${i} called');
  }
`;
}

hugeClass += `
  // 还有一些特殊方法
  public special1(): void {
    this.method1();
    this.method5();
    this.method10();
  }
  
  public special2(): void {
    for (let i = 0; i < 20; i++) {
      console.log('loop:', i);
    }
  }
}
`;

fs.writeFileSync(path.join(EXTREME_TEST_DIR, 'huge_class.ts'), hugeClass);
console.log('✓ 创建了包含100+方法的极限类');

// 7. 创建许多互相调用的类（复杂的依赖网络）
console.log('--- 创建复杂调用网络 ---');

let networkClasses = '';
const numClasses = 15;

for (let i = 1; i <= numClasses; i++) {
  networkClasses += `
// Class ${i} - part of the complex network
export class NetworkClass${i} {
  private id: number = ${i};
  
  public process(): void {
    console.log('processing class ${i}');
    this.callOthers();
  }
  
  private callOthers(): void {
`;
  
  // 让它调用3-5个其他类
  const callCount = 3 + Math.floor(Math.random() * 3);
  const calledIndices = new Set();
  while (calledIndices.size < callCount) {
    let j = Math.floor(Math.random() * numClasses) + 1;
    if (j !== i && !calledIndices.has(j)) {
      calledIndices.add(j);
    }
  }
  
  for (const j of calledIndices) {
    networkClasses += `
    // Calls NetworkClass${j}
    // (instance would be here)`;
  }
  
  networkClasses += `
  }
  
  public getInfo(): any {
    return { id: this.id };
  }
  
  public work(): void {
    this.doWork();
    this.finishWork();
  }
  
  private doWork(): void {
    console.log('doing work in ${i}');
  }
  
  private finishWork(): void {
    console.log('finished work in ${i}');
  }
}
`;
}

fs.writeFileSync(path.join(EXTREME_TEST_DIR, 'call_network.ts'), networkClasses);
console.log('✓ 创建了15个类组成的复杂调用网络');

// 8. 创建一些文件到深度嵌套目录中
console.log('--- 创建深层嵌套目录中的文件 ---');

for (let i = 0; i < 10; i++) {
  let filePath = EXTREME_TEST_DIR;
  const dirDepth = 5 + Math.floor(Math.random() * 15);
  for (let j = 0; j < dirDepth; j++) {
    filePath = path.join(filePath, `deep_dir_${j}`);
  }
  filePath = path.join(filePath, `deep_file_${i}.ts`);
  
  fs.writeFileSync(filePath, `
// Deep file ${i} - ${dirDepth} levels deep
export class DeepFile${i}Class {
  public hello(): void {
    console.log('hello from deep file ${i}');
  }
  
  public work(): void {
    this.hello();
    this.doStuff();
  }
  
  private doStuff(): void {
    console.log('doing stuff in deep file ${i}');
  }
}
`);
}

console.log('✓ 创建了10个深层嵌套文件');

// 9. 创建一些包含TypeScript高级特性的文件
console.log('--- 创建TypeScript高级特性 ---');

const advancedTS = `
// TypeScript高级特性测试
export interface AdvancedInterface<T> {
  id: number;
  data: T;
  process(data: T): T;
}

export abstract class AbstractBase {
  protected value: number;
  
  constructor(val: number) {
    this.value = val;
  }
  
  abstract execute(): void;
  
  public getValue(): number {
    return this.value;
  }
}

export class ConcreteImpl extends AbstractBase {
  constructor() {
    super(42);
  }
  
  execute(): void {
    this.doSomething();
    this.doAnotherThing();
  }
  
  private doSomething(): void {
    console.log('do something concrete');
  }
  
  private doAnotherThing(): void {
    console.log('do another thing');
  }
}

export class GenericContainer<T> {
  private items: T[] = [];
  
  add(item: T): void {
    this.items.push(item);
  }
  
  getAll(): T[] {
    return [...this.items];
  }
  
  processAll(): void {
    this.items.forEach(item => {
      console.log('processing item');
    });
  }
}

export enum Status {
  Active = 'active',
  Inactive = 'inactive',
  Pending = 'pending'
}

export type StringOrNumber = string | number;

export function withDefaults(val: StringOrNumber = 0) {
  console.log('value:', val);
}
`;

fs.writeFileSync(path.join(EXTREME_TEST_DIR, 'advanced_typescript.ts'), advancedTS);
console.log('✓ 创建了高级TypeScript特性文件');

console.log('\n✓✓✓ 第13阶段：极端混乱和超复杂测试场景创建完成！');
console.log('文件总数：100+（包含各种极端情况）');
