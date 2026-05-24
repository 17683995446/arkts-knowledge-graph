/**
 * 继承层次结构 - 中间层 1
 */

import { BaseClass0 } from './Inheritance0';

export abstract class BaseClass1 extends BaseClass0 {
    intermediateMethod(): void {
        console.log('intermediate method 1');
    }
}
