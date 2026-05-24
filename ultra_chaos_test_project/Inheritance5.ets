/**
 * 继承层次结构 - 中间层 5
 */

import { BaseClass4 } from './Inheritance4';

export abstract class BaseClass5 extends BaseClass4 {
    intermediateMethod(): void {
        console.log('intermediate method 5');
    }
}
